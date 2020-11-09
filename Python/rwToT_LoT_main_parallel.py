from sqlalchemy import create_engine
import pandas as pd
import datetime
import sys 
import time
import multiprocessing
import copy
import os
import numpy as np
import psutil  # to set the NICENESS of the processes

import rwToT_LoT_line as ln
import rwToT_LoT_functions as fn
import rwToT_LoT_read_param as rp

nprocesses = (multiprocessing.cpu_count()-1 or 1)
nchunks = nprocesses

nprocesses = 1
nchunks = 1

NSUPERCHUNKS = 1  #  The input data is split into N superchunks, and each superchunk then split into nprocesses chunks and processed in parallel
                   #  Each superchunk is processed sequentially and the processing results are appended to the main output data frame


cases = rp.cases('mcc')  # dummy initialization.  Actual indication will be updated in the main function


class Input:
  def __init__(self,
               r_window, 
               l_disgap,
               drug_switch_ignore,
               combo_dropped_line_advance,
               indication,
               database,
               filename,
               outfile,
               data,
               unique_patients):
    self.r_window = r_window
    self.l_disgap = l_disgap
    self.drug_switch_ignore = drug_switch_ignore
    self.combo_dropped_line_advance = combo_dropped_line_advance
    self.indication = indication
    self.database = database
    self.filename = filename
    self.outfile = outfile
    self.data = data
    self.unique_patients = unique_patients
    self.index_date = pd.to_datetime('2001-01-01')
    self.last_activity_date = pd.to_datetime('2001-01-01')
    self.last_enrollment_date = pd.to_datetime('2001-01-01')
    
class Patient:
    def __init__(self):
        self.data = pd.DataFrame()
        self.line_number = 0
        self.line_name = None
        self.line_type = None
        self.line_start = None
        self.line_end = None
        self.line_next_start = None
        self.line_end_reason = None
        self.previous_line = None
        self.line_is_maintenance = False
        self.is_next_maintenance = False
        self.line_add_exemption = None
        self.line_sub_exemption = None
        self.line_gap_exemption = None
        self.line_name_exemption = None
        self.regimen = list()
        self.cut = pd.DataFrame()

patient = Patient()



def process_chunk(chunk_patients):    # equivalent of just_wait_and_print_len_and_idx(df)

    patient = Patient()
    
    output_lot = pd.DataFrame()
    output_doses = pd.DataFrame()
    
    
    print("Processing chunk")
    print("Process id ", os.getpid())
    print("Data frame dimensions: ", chunk_patients.data.shape, flush = True)

    for i in range(len(chunk_patients.unique_patients)):
        
        patient.data = chunk_patients.data.query('PATIENT_ID == %s' % chunk_patients.unique_patients[i]).reset_index(drop = True)
        patient.data = patient.data.sort_values('MED_START').reset_index(drop = True)
        chunk_patients.index_date = patient.data.loc[0, 'MED_START']
        chunk_patients.last_activity_date = None # patient.data.loc[0, ['LAST_ACTIVITY_DATE']]
        chunk_patients.last_enrollment_date = None # patient.data.loc[0, ['LAST_ENROLLMENT_DATE']]
        # Scan patient claims data to acquire line information on a step-wise line by line basis

        # patient.data is now a dataframe which contains drug administration entries ordered by date
        # we need to add a column to this indicating the cycle
        # the cycle should reset with the new line, but here we just increase the cycle number as soon as
        # it's been more than four days since the last drug administration.  Call this cycle_tmp
        for entry in patient.data.index:
            if entry == 0:
                patient.data.loc[entry, 'CYCLE'] = 1
                patient.data.loc[entry, 'CYCLE_START'] = patient.data.loc[entry, 'MED_START']
            else:
                if patient.data.loc[entry, 'MED_START'] - datetime.timedelta(days = 4) > patient.data.loc[entry - 1, 'MED_START']:
                    patient.data.loc[entry, 'CYCLE'] = patient.data.loc[entry - 1, 'CYCLE'] + 1
                else:
                    patient.data.loc[entry, 'CYCLE'] = patient.data.loc[entry - 1, 'CYCLE']
        patient.data['CYCLE_START'] = patient.data.groupby('CYCLE')['MED_START'].transform("min")
        patient.data['CYCLE_END'] = patient.data.groupby('CYCLE')['MED_END'].transform("max")
        patient.data['CYCLE_REGIMEN'] = patient.data.groupby('CYCLE')['MED_NAME'].transform(lambda x: ', '.join(sorted(x.unique())))

        
        for entry in patient.data.index:
            if patient.data.loc[entry, 'CYCLE'] == 1:
                patient.data.loc[entry, 'PRIOR_CYCLE_REGIMEN'] = None 
                patient.data.loc[entry, 'TWO_CYCLES'] = False 
            else:
                current_cycle = patient.data.loc[entry, 'CYCLE']
                prior_cycle_index = patient.data.index[patient.data['CYCLE'] == current_cycle - 1].min()
                prior_cycle_regimen = patient.data.loc[prior_cycle_index, 'CYCLE_REGIMEN']
                patient.data.loc[entry, 'PRIOR_CYCLE_REGIMEN'] = prior_cycle_regimen
                if (all(drug in prior_cycle_regimen for drug in patient.data.loc[entry, 'CYCLE_REGIMEN']) 
                    and all(drug in patient.data.loc[entry, 'CYCLE_REGIMEN'] for drug in prior_cycle_regimen)):
                    patient.data.loc[entry, 'TWO_CYCLES'] = True 
                else:
                    patient.data.loc[entry, 'TWO_CYCLES'] = False 
    
                
        # set medication start and medication end the same for all drugs in the same cycle
        patient.data['ORIGINAL_MED_START'] = patient.data['MED_START']
        patient.data['ORIGINAL_MED_END'] = patient.data['MED_END']
        patient.data['MED_START'] = patient.data['CYCLE_START']
        patient.data['MED_END'] = patient.data['CYCLE_START']

        
        # Initialize the line number and other parameters to their initial values
        patient.line_number = 0
        patient.previous_line = None
        patient.is_next_maintenance = False

        # while loop here
        patient.line_next_start = chunk_patients.data.loc[0, 'MED_START'] + datetime.timedelta(days = chunk_patients.r_window)

        while len(patient.data.index) > 0:

            # Get Regimen and Line Start Information
            patient.regimen = ln.get_regimen(patient.data, chunk_patients.r_window)

             # Acquire rest of line data
            patient.f_line_data = ln.get_line_data(patient.data, patient.regimen, chunk_patients.l_disgap, patient.line_number, patient.is_next_maintenance, chunk_patients.r_window, chunk_patients.drug_switch_ignore, chunk_patients.combo_dropped_line_advance, chunk_patients.indication, cases)
            patient.line_name = patient.f_line_data['line_name']
            patient.line_type = patient.f_line_data['line_type']
            patient.line_start = patient.f_line_data['line_start']
            patient.line_end = patient.f_line_data['line_end']
            patient.line_next_start = patient.f_line_data['line_next_start']
            patient.line_end_reason = patient.f_line_data['line_end_reason']
            patient.line_number = patient.f_line_data['line_number']
            patient.line_is_maintenance = patient.f_line_data['line_is_maintenance']
            patient.is_next_maintenance = patient.f_line_data['line_is_next_maintenance']
            patient.line_add_exemption = patient.f_line_data['line_add_exemption']
            patient.line_sub_exemption = patient.f_line_data['line_sub_exemption']
            patient.line_gap_exemption = patient.f_line_data['line_gap_exemption']
            patient.line_name_exemption = patient.f_line_data['line_name_exemption']

            # Acquire dosage information associated with this line
            if patient.line_next_start == None:
                patient.output_doses = patient.data
            else:
                patient.output_doses = patient.data[patient.data['MED_START'] < patient.line_next_start]

            # Append line data to final output
            patient.output_lot = pd.DataFrame({'PATIENT_ID' : str(chunk_patients.unique_patients[i]),
                               'LINE_NUMBER' : str(patient.line_number),
                               'LINE_NAME' : patient.line_name,
                               'START_DATE' : patient.line_start,
                               'END_DATE' : patient.line_end,
                               'LINE_TYPE' : patient.line_type,
                               'IS_MAINTENANCE' : patient.line_is_maintenance,
                               'ADD_EXEMPTION' : patient.line_add_exemption,
                               'SUB_EXEMPTION' : patient.line_sub_exemption,
                               'GAP_EXEMPTION' : patient.line_gap_exemption,
                               'NAME_EXEMPTION' : patient.line_name_exemption,
                               'LINE_END_REASON' : patient.line_end_reason,
                               'ENHANCED_COHORT' : chunk_patients.indication,
                               'INDEX_DATE' : chunk_patients.index_date},
                                columns=['PATIENT_ID','LINE_NUMBER','LINE_NAME', 'START_DATE', 'END_DATE',
                                        'LINE_TYPE', 'IS_MAINTENANCE', 
                                         'ADD_EXEMPTION', 'SUB_EXEMPTION', 'GAP_EXEMPTION', 'NAME_EXEMPTION',
                                        'LINE_END_REASON', 'ENHANCED_COHORT', 'INDEX_DATE'],
                                          index = [1])
            #output_lot = output_lot.append(patient.output_lot, ignore_index = True)
            output_lot = pd.concat([output_lot, patient.output_lot], ignore_index = True)
            
            # Append patient dosage information w/ line information
            patient.output_doses = patient.output_doses[['PATIENT_ID', 'MED_START', 'MED_END', 'MED_NAME']]
            patient.output_doses['LINE_NUMBER'] = patient.line_number
            patient.output_doses['LINE_NAME'] = patient.line_name
            patient.output_doses['MED_NAME'] = patient.output_doses['MED_NAME'].str.upper()
            output_doses = pd.concat([output_doses, patient.output_doses], ignore_index = True)

            patient.previous_line = patient.line_number

            # Cut the data to the next line
            if patient.line_next_start == None:
                break
            patient.cut = fn.snip_dataframe(patient.data, patient.line_next_start)
            patient.data = patient.cut['after']
        
    return output_lot, output_doses
    


def main():

    ##################################
    ### hardcoded input parameters ###
    ##################################

    patient = Patient()
    
    global input
    global cases
    
    command_line_indication = sys.argv[1].upper()
    
    input = Input(r_window = 28,                       # default value, to be changed by the value in the table
                  l_disgap = 180,                      # default value, to be changed by the value in the table
                  drug_switch_ignore = False,          # default value, to be changed by the value in the table
                  combo_dropped_line_advance = False,  # default value, to be changed by the value in the table
                  indication = command_line_indication,
                  database = "Test",
                  filename = "example_input.csv",
                  outfile = "Test",
                  data = pd.DataFrame(),
                  unique_patients = list())

    cases = rp.cases(input.indication)

    # Reset default input parameters if necessary
    input.r_window = int(cases.par_general.loc[0, 'r_window'])
    input.l_disgap = int(cases.par_general.loc[0, 'l_disgap'])
    input.drug_switch_ignore = cases.par_general.loc[0, 'drug_switch_ignore']
    input.combo_dropped_line_advance = cases.par_general.loc[0, 'combo_dropped_line_advance']
    
    ##############################
    ### Load Preprocessed Data ### 
    ##############################


    input.data = pd.read_csv('data/' + command_line_indication.upper() + '/' + input.database + '/' + input.filename)
    input.data['MED_START'] = pd.to_datetime(input.data['MED_START'])
    input.data['MED_END'] = pd.to_datetime(input.data['MED_START'])
    input.unique_patients = input.data['PATIENT_ID'].unique()
    print("Number of unique patients: " + str(len(input.unique_patients)))

    
    input_chunk = []
    for i in range(nchunks):
        print("Initializing chunk ", i, flush = True)    
        input_chunk.append(Input(r_window = 28,                       # default value, to be changed by the value in the table
                                 l_disgap = 180,                      # default value, to be changed by the value in the table
                                 drug_switch_ignore = False,          # default value, to be changed by the value in the table
                                 combo_dropped_line_advance = False,  # default value, to be changed by the value in the table
                                 indication = None,
                                 database = "Test",
                                 filename = "example_input.csv",
                                 outfile = "test",
                                 data = pd.DataFrame(),
                                 unique_patients = list()))


    chunk_size = int(len(input.unique_patients)/nchunks) + 1
    # try to get only a small part of the database 
    chunk_size = int(chunk_size/NSUPERCHUNKS) + 1

    ##################################################
    ### Blank template of final output to be saved ###
    ##################################################

    output_lot = pd.DataFrame()
    output_doses = pd.DataFrame()
    
    ####################
    ### Script start ###
    ####################
    
    output_lot_tmp = pd.DataFrame()
    output_doses_tmp = pd.DataFrame()

    start = time.time()

    
    
    
    starting_patient = 0
    while (starting_patient < int((len(input.unique_patients) - 1))):  # try a couple of first chapters of BREAST
        print("Starting the next part of the database with patient", starting_patient, flush = True)
        for i in range(nchunks):
            print("Populating data for chunk ", i, flush = True)
            # Reset default input parameters if necessary
            input_chunk[i].indication = command_line_indication
            input_chunk[i].r_window = int(cases.par_general.loc[0, 'r_window'])
            input_chunk[i].l_disgap = int(cases.par_general.loc[0, 'l_disgap'])
            input_chunk[i].drug_switch_ignore = cases.par_general.loc[0, 'drug_switch_ignore']
            input_chunk[i].combo_dropped_line_advance = cases.par_general.loc[0, 'combo_dropped_line_advance']
            print("Range of patients: ", i*chunk_size+starting_patient, (i+1)*chunk_size+starting_patient)
            input_chunk[i].data = input.data[input.data['PATIENT_ID'].isin(input.unique_patients[(i*chunk_size+starting_patient):((i+1)*chunk_size+starting_patient)])].reset_index(drop = True)
            input_chunk[i].unique_patients = input_chunk[i].data['PATIENT_ID'].unique()     

        # Loop through chunks   

        ctx = multiprocessing.get_context('spawn')
        pool = ctx.Pool(nprocesses)
        processes = [p.pid for p in pool._pool]
        for pid in processes:
            p = psutil.Process(pid)
            p.nice(5)
        pool_results = pool.map(process_chunk, input_chunk)
        pool.close()
        pool.join()
        results = []
        for result in pool_results:
            results.extend(result)
        output_lot_tmp = pd.concat(results[::2])
        output_doses_tmp = pd.concat(results[1::2])
        
        print("Output_lot_tmp memory usage", output_lot_tmp.memory_usage(deep = True).sum(), flush = True)
        print("Output_doses_tmp memory usage", output_doses_tmp.memory_usage(deep = True).sum(), flush = True)

        output_lot = output_lot.append(output_lot_tmp, ignore_index = True)
        output_doses = output_doses.append(output_doses_tmp, ignore_index = True)

        starting_patient = starting_patient + chunk_size * nchunks
    
    
    
    end = time.time()
    
    
    print("Final output_lot dimensions", output_lot.shape, flush = True)
    print("Final output_lot memory usage", output_lot.memory_usage(deep = True).sum(), flush = True)
    print("Final output_doses dimensions", output_doses.shape, flush = True)
    print("Final output_doses memory usage", output_doses.memory_usage(deep = True).sum(), flush = True)
    
    print('Time to run the main code: ' + str(end - start) + ' seconds')

    if not os.path.exists('./output'):
        os.makedirs('./output')

    if not os.path.exists('./output/' + input.indication.upper()):
        os.makedirs('./output/' + input.indication.upper())

    if not os.path.exists('./output/' + input.indication.upper() + '/' + input.outfile):
        os.makedirs('./output/' + input.indication.upper()+ '/' + input.outfile)


    output_lot.to_csv('./output/' + input.indication.upper() + '/' + input.outfile + '/output_lot.csv', index = False)
    output_doses.to_csv('./output/' + input.indication.upper() + '/' + input.outfile + '/output_doses.csv', index = False)
    

if __name__ == '__main__':
    main()
