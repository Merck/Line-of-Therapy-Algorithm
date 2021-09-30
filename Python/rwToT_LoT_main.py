import pandas as pd
import datetime
import sys 

import rwToT_LoT_line as ln
import rwToT_LoT_functions as fn
import rwToT_LoT_import as im

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
    

def main():

    ##################################
    ### hardcoded input parameters ###
    ##################################

    input = Input(r_window = 28,
                  l_disgap = 180,
                  drug_switch_ignore = False,
                  combo_dropped_line_advance = False,
                  indication = "NSCLC",
                  database = "Test",
                  filename = "example_input.csv",
                  outfile = "test",
                  data = pd.DataFrame(),
                  unique_patients = list())

    cases = im.cases(input.indication)

    ##############################
    ### Load Preprocessed Data ### 
    ##############################

    input.data = pd.read_csv("./data/" + input.indication + "/" + input.database + "/" + input.filename).drop_duplicates()
    #input.data = pd.read_csv("../../processed_input_all.csv").drop_duplicates()
    #input.data = pd.read_csv("../../patient1184401.csv").drop_duplicates()

    input.unique_patients = input.data['PATIENT_ID'].unique()
    print("Number of unique patients: " + str(len(input.unique_patients)))

    input.data['MED_START'] = pd.to_datetime(input.data['MED_START'])
    input.data['MED_END'] = pd.to_datetime(input.data['MED_END'])
    input.data['MED_NAME'] = input.data['MED_NAME'].str.lower()

    #print(input.data)
    #print(input.unique_patients)

    ##################################################
    ### Blank template of final output to be saved ###
    ##################################################

    # The R version first defines the columns of the output dataframes
    # output_lot = pd.DataFrame({'PATIENT_ID' : str(),
    #                            'LINE_NUMBER' : str(),
    #                            'LINE_NAME' : str(),
    #                            'START_DATE' : pd.to_datetime(str()),
    #                            'END_DATE' : pd.to_datetime(str()),
    #                            'LINE_TYPE' : str(),
    #                            'IS_MAINTENANCE' : bool(),
    #                            'ADD_EXEMPTION' : bool(),
    #                            'SUB_EXEMPTION' : bool(),
    #                            'GAP_EXEMPTION' : bool(),
    #                            'NAME_EXEMPTION' : bool(),
    #                            'LINE_END_REASON' : str(),
    #                            'ENHANCED_COHORT' : str(),
    #                            'INDEX_DATE' : pd.to_datetime(str())},
    #                           index = [1])
    
    
    
    # output_doses = pd.DataFrame({'PATIENT_ID' : str(),
    #                              'MED_START' : pd.to_datetime(str()),
    #                              'MED_END' : pd.to_datetime(str()),
    #                              'MED_NAME' : str(),
    #                              'LINE_NUMBER' : str(),
    #                              'LINE_NAME' : str()}, 
    #                             index = [1])
    #
    # In Python this creates and extra empty row at the top.  
    # We do not need to specify column names beforehand, just a simple declaration is sufficients

    output_lot = pd.DataFrame()
    output_doses = pd.DataFrame()
    

    ####################
    ### Script start ###
    ####################

    # Create tmp class to use within the following loop
    class Tmp:
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

    tmp = Tmp()

    # Loop through unique patients
    for i in range(len(input.unique_patients)):
        if abs(i/100 - i//100) < 0.001:
            print("Processing patient " + str(i))
        tmp.data = input.data.query('PATIENT_ID == %s' % input.unique_patients[i]).reset_index(drop = True)
        tmp.data = tmp.data.sort_values('MED_START')
        input.index_date = tmp.data.loc[0, 'MED_START']
        input.last_activity_date = None # tmp.data.loc[0, ['LAST_ACTIVITY_DATE']]
        input.last_enrollment_date = None # tmp.data.loc[0, ['LAST_ENROLLMENT_DATE']]
        # Scan patient claims data to acquire line information on a step-wise line by line basis
  
        # Initialize the line number and other parameters to their initial values
        tmp.line_number = 0
        tmp.previous_line = None
        tmp.is_next_maintenance = False
        
        # while loop here
        tmp.line_next_start = input.data.loc[0, 'MED_START'] + datetime.timedelta(days = input.r_window)

        while len(tmp.data.index) > 0:
    
            # Get Regimen and Line Start Information
            tmp.regimen = ln.get_regimen(tmp.data, input.r_window)
            
             # Acquire rest of line data
            tmp.f_line_data = ln.get_line_data(tmp.data, tmp.regimen, input.l_disgap, tmp.line_number, tmp.is_next_maintenance, input.r_window, input.drug_switch_ignore, input.combo_dropped_line_advance, input.indication)
            tmp.line_name = tmp.f_line_data['line_name']
            tmp.line_type = tmp.f_line_data['line_type']
            tmp.line_start = tmp.f_line_data['line_start']
            tmp.line_end = tmp.f_line_data['line_end']
            tmp.line_next_start = tmp.f_line_data['line_next_start']
            tmp.line_end_reason = tmp.f_line_data['line_end_reason']
            tmp.line_number = tmp.f_line_data['line_number']
            tmp.line_is_maintenance = tmp.f_line_data['line_is_maintenance']
            tmp.is_next_maintenance = tmp.f_line_data['line_is_next_maintenance']
            tmp.line_add_exemption = tmp.f_line_data['line_add_exemption']
            tmp.line_sub_exemption = tmp.f_line_data['line_sub_exemption']
            tmp.line_gap_exemption = tmp.f_line_data['line_gap_exemption']
            tmp.line_name_exemption = tmp.f_line_data['line_name_exemption']

            # Acquire dosage information associated with this line
            if tmp.line_next_start == None:
                tmp.output_doses = tmp.data
            else:
                tmp.output_doses = tmp.data[tmp.data['MED_START'] < tmp.line_next_start]
                
            # Append line data to final output
            tmp.output_lot = pd.DataFrame({'PATIENT_ID' : str(input.unique_patients[i]),
                               'LINE_NUMBER' : str(tmp.line_number),
                               'LINE_NAME' : tmp.line_name,
                               'START_DATE' : tmp.line_start,
                               'END_DATE' : tmp.line_end,
                               'LINE_TYPE' : tmp.line_type,
                               'IS_MAINTENANCE' : tmp.line_is_maintenance,
                               'ADD_EXEMPTION' : tmp.line_add_exemption,
                               'SUB_EXEMPTION' : tmp.line_sub_exemption,
                               'GAP_EXEMPTION' : tmp.line_gap_exemption,
                               'NAME_EXEMPTION' : tmp.line_name_exemption,
                               'LINE_END_REASON' : tmp.line_end_reason,
                               'ENHANCED_COHORT' : input.indication,
                               'INDEX_DATE' : input.index_date},
                                          index = [1])
            output_lot = output_lot.append(tmp.output_lot, ignore_index = True)

            # Append patient dosage information w/ line information
            tmp.output_doses = tmp.output_doses[['PATIENT_ID', 'MED_START', 'MED_END', 'MED_NAME']]
            tmp.output_doses['LINE_NUMBER'] = tmp.line_number
            tmp.output_doses['LINE_NAME'] = tmp.line_name
            tmp.output_doses['MED_NAME'] = tmp.output_doses['MED_NAME'].str.upper()
    
            output_doses = output_doses.append(tmp.output_doses, ignore_index = True)
 
            tmp.previous_line = tmp.line_number
    
            # Cut the data to the next line
            if tmp.line_next_start == None:
                break
            tmp.cut = fn.snip_dataframe(tmp.data, tmp.line_next_start)
            tmp.data = tmp.cut['after']
    #print(output_lot)
    #print(output_doses)

    output_lot.to_csv("./output/" + input.indication + "/" + input.database + "/output_lot_" + input.outfile + ".csv", index = False)
    output_doses.to_csv("./output/" + input.indication + "/" + input.database + "/output_doses_" + input.outfile + ".csv", index = False)
    input.data.to_csv("./output/" + input.indication + "/" + input.database + "/processed_input_" + input.outfile + ".csv", index = False)

    # print("Testing the import script.")
    # print("Line name:")
    # print(cases.line_name)
    # print("Line substitutions:")
    # print(cases.line_substitutions)
    # print("Episode gap:")
    # print(cases.episode_gap)


    # print("Testing get_drug_summary function")
    # line_end_date = datetime.datetime.now()
    # drug_summary = fn.get_drug_summary(input.data, input.r_window, line_end_date)
    # print(drug_summary)

if __name__ == '__main__':
    main()
