import datetime

import rwToT_LoT_functions as fn
#import rwToT_LoT_import as im
#import rwToT_LoT_read_param as rp

def get_regimen(df, r_window):

    # Start of line from the first row, which is assumed to be first drug epsiode 
    # (accomplished via cut_to_first_dose function)
    # Later in the code/process, this line start is double checked and challenged 
    # if there is an eligible drug switch

    tmp_line_start = df.loc[0, 'MED_START']


    # Set the regimen window relative to the line start

    regimen_end_date = tmp_line_start + datetime.timedelta(days = r_window)
  

    # Take the line start date, then project to regimen defining window, 
    # and get unique list of medications
    tmp_regimen = df[df['MED_START'] <= regimen_end_date] 
    output_regimen = tmp_regimen['MED_NAME'].unique()
  
    ############# RETURN #############
    return(output_regimen)



################################################################################################
### Get Line Data Function                                                                   ###
### function returns relevant line of therapy information such as line name, line end date,  ###
### is maintenance therapy, next line start date, line type, and line end reason             ###
### Inputs: 1) claims dataframe, 2) regimen, 3) discontinuation gap (days), 4) line number   ###
### Outputs: 1) line name, 2) line end date, 3) next line start date, 4) line type,          ###
### 5) line end reason, 6) is maintenance therapy                                            ###
### General Steps:                                                                           ###
### 1. Check if we hit last row of table - if so then there is no further data to analyze    ###
### and we stop here, setting end date to be the last date activity                          ###
### 2. Check if there is a gap between the current drug date for that line. If there is,     ###
### then we move to the second pass of checks                                                ###
### 3. Check if the the next drug is a drug not within the regimen. If there is,             ###
### then we move to the second pass of checks                                                ###
### 4. Second pass - analyze combo treatment and determine the correct discontinuation date  ###
### and account for drug introduction                                                        ###
### 5. Second pass - analyze the discontinuations and account for exceptions                 ###
### to discontinuations based on medication                                                  ###
### 6. Second pass- analyze if the treatment is maintenance therapy. If it is,               ###
### then label it as such and do not advance line number                                     ###
### 7. Compute final outputs and return it                                                   ###
################################################################################################

def get_line_data(df, 
                  r_regimen, 
                  l_disgap, 
                  l_line_number, 
                  l_is_next_maintenance, 
                  input_r_window, 
                  input_drug_switch_ignore, 
                  input_combo_dropped_line_advance,
                  input_indication,
                  cases):
    #cases = im.cases(input_indication)
    #cases = rp.cases(input_indication)
    cases = cases

    # Set assumptions
    line_is_maintenance = False
    if (len(r_regimen) > 1):
        line_type = "combo"
    else:
        line_type = "mono"
    line_line_number = l_line_number
    line_line_start = None
    adjusted_line_start = None  # V.S. 10/01/20
    line_end_date_less_than_flag = False
    line_is_next_maintenance = l_is_next_maintenance
    
    has_eligible_drug_addition = False
    has_eligible_drug_substition = False
    has_gap_exemption = False
    has_line_name_exemption = False

    ############### First Pass Checks #################
    # If we hit the last row in the claims database, then stop and return outputs
    if (len(df.index) == 1): 
        line_end_date = df.loc[0, 'MED_END']
        line_end_reason = "Last row hit"
        line_next_start = None
        # Scan all rows in the claims database and grab information on the  
        # current drug and the next drug in the timeline
    else:
        for i in range(1, len(df.index)): 
            # Grab information on current drug and next drug
            current_drug = df.loc[i-1, 'MED_NAME']
            current_drug_date = df.loc[i-1, 'MED_START']
            current_drug_end = df.loc[i-1, 'MED_END']
            next_drug = df.loc[i, 'MED_NAME']
            next_drug_date = df.loc[i, 'MED_START']
            remaining_drugs = df.loc[i:(len(df.index)-1), :]
            has_eligible_drug_addition = fn.is_eligible_drug_addition(next_drug, cases.line_additions)
            has_eligible_drug_substition = fn.is_eligible_drug_substitution(next_drug, r_regimen, cases.line_substitutions)
            has_gap_exemption = fn.is_excluded_from_gap(r_regimen, remaining_drugs, list(cases.episode_gap['drug_name']))

            two_cycles = df.loc[i-1, 'TWO_CYCLES']      #  V.S. 2020/10/01 - Cycle check

            # If you hit the last row in the scan, then stop and return outputs
            if (i == len(df.index)-1) and ((next_drug in r_regimen) or has_eligible_drug_substition or has_eligible_drug_addition): 
                if ((next_drug_date - current_drug_end).days > l_disgap) and (has_gap_exemption == False):
                    line_end_date = current_drug_end
                    line_end_reason = "Passed discontinuation gap"
                    line_next_start = next_drug_date
                else:
                    line_end_date = df.loc[i, 'MED_END']
                    line_end_reason = "Last row hit"
                    line_next_start = None
                break
       
            # Check if the gap between the next drug and current drug is wider than the discontinuation gap
            elif (next_drug_date - current_drug_end).days > l_disgap:
                # If drug is excluded from the discontinuation gap, then skip whole process and go to the next drug
                if (has_gap_exemption):
                    continue
                line_end_date = current_drug_end
                line_end_reason = "Passed discontinuation gap"
                line_next_start = next_drug_date
                break

                
            # Line is not advanced because two-cycle rule is not met    
            elif (next_drug in r_regimen) == False and (has_eligible_drug_addition == False) and (has_eligible_drug_substition == False) and two_cycles == False:   # V.S. 2020/10/01
                r_regimen = df[df['CYCLE']==df.loc[i, 'CYCLE']]['MED_NAME'].unique()                                                                                # V.S. 2020/10/01
                drug_dates = df[df['MED_NAME'].isin(r_regimen)]['MED_START']                                                                                        # V.S. 2020/10/01
                adjusted_line_start = min(drug_dates)                                                                                                               # V.S. 2020/10/01
                line_end_date = max(drug_dates)                                                                                                                     # V.S. 2020/10/01
                line_end_reason = "New line started with new drugs"                                                                                                 # V.S. 2020/10/01
                line_next_start = next_drug_date                                                                                                                    # V.S. 2020/10/01
                
            # Check if the next drug is not part of the regimen
            elif (next_drug in r_regimen) == False and (has_eligible_drug_addition == False) and (has_eligible_drug_substition == False):
                temp_check_new_regimen = df[df['MED_START'] == current_drug_end]#['MED_NAME']
                temp_med_name = list(temp_check_new_regimen['MED_NAME'])
                all_temp_med_name_are_in_r_regimen =  all(elem in r_regimen  for elem in temp_med_name)
                line_end_date_less_than_flag = (all_temp_med_name_are_in_r_regimen == False)
        
                if (line_end_date_less_than_flag):
                    temp_line_end_df = df[df['MED_START'] < current_drug_end]
                else:
                    temp_line_end_df = df[df['MED_START'] <= current_drug_end]

                line_end_date = max(temp_line_end_df['MED_START'])
                line_end_reason = "New line started with new drugs"
                line_next_start = next_drug_date

                break
    # End first pass of checks
  
  
    ################### Second pass on combo treatment to detect supressions and gaps ###################
  
    # Get Drug Summary information
    line_drug_summary = fn.get_drug_summary(df, input_r_window, line_end_date)
 
    # Re-compute line name and line start date
    check_line_name = fn.check_line_name(r_regimen, line_drug_summary, cases.line_name, input_r_window, input_drug_switch_ignore)
    line_name = check_line_name['line_name']
    line_line_start = check_line_name['line_start']
    if adjusted_line_start:                                 # V.S. 10/01/2020
        line_line_start = adjusted_line_start               # V.S. 10/01/2020
    has_line_name_exemption = check_line_name['line_switched']
  
    # Compute Line Type
    # test this block.  Why is there [[1]] in the original R script?  
    tmp_line_regimen = line_name.split(',')
    if len(tmp_line_regimen) == 1:
        line_type = "mono"
    else: 
        line_type = "combo"
  
    # Re-compute if combo therapy dropped drugs should trigger a new line
    if (line_type == "combo") and input_combo_dropped_line_advance:
        check_combo_dropped_drugs = fn.check_combo_dropped_drugs(line_drug_summary, line_end_date, line_next_start, line_end_reason)
        line_end_date = check_combo_dropped_drugs['line_end_date']
        line_end_reason = check_combo_dropped_drugs['line_end_reason']
        line_next_start = check_combo_dropped_drugs['line_next_start']

  
    # Check to see if the current line is maintenance therapy
    if line_line_number == 1:
    
        if line_is_next_maintenance:
            line_is_maintenance = True
        
        else:
            line_is_maintenance = fn.is_eligible_switch_maintenance(r_regimen, cases.line_maintenance, line_line_number)
        
        line_is_next_maintenance = False

    # Check for continuation maintenance therapy within the combo treatment
    elif (line_type == "combo") and (line_line_number == 0):
        line_is_next_maintenance = fn.is_eligible_continuation_maintenance(r_regimen, cases.line_maintenance, line_line_number, line_drug_summary)
    
        # If the line is eligible for maintenance and is combo, then split it
        if line_is_next_maintenance:
            line_was_previous_maintenance = True
            tmp_drug_group_dropped = line_drug_summary[line_drug_summary['DROPPED'] == 1]
            line_next_start = max(tmp_drug_group_dropped['LAST_SEEN']) + datetime.timedelta(days = input_r_window)
            line_end_reason = "Entering continuation maintenance therapy"
  
    ########### Compute remaining final outputs ############
    if (line_is_maintenance == False) or (line_line_number == 0):
        line_line_number = line_line_number + 1

    ############# RETURN #############
    return({'line_name' : line_name, 
            'line_type' : line_type, 
            'line_start' : line_line_start, 
            'line_end' : line_end_date, 
            'line_next_start' : line_next_start, 
            'line_end_reason' : line_end_reason, 
            'line_number' : line_line_number, 
            'line_is_maintenance' : line_is_maintenance, 
            'line_is_next_maintenance' : line_is_next_maintenance,
            'line_add_exemption' : has_eligible_drug_addition,
            'line_sub_exemption' : has_eligible_drug_substition,
            'line_gap_exemption' : has_gap_exemption,
            'line_name_exemption' : has_line_name_exemption})
  


    
