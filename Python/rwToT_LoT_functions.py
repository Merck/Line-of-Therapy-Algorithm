import pandas as pd 
from datetime import datetime
from datetime import timedelta

####################################################################
### Check Line Name Function                                     ###
### This checks for special cases to determine line name         ###
### Input: regimen, drug summary, and list of special cases      ###
### Output: line name                                            ###
### Python Version Copyright (c) 2020 Pablo Delgado,             ###
### Merck Sharp & Dohme Corp.                                    ###
### a subsidiary of Merck & Co., Inc., Kenilworth, NJ, USA.      ###
####################################################################

def check_line_name(regimen, drug_summary, cases, input_r_window, input_drug_switch_ignore):
    # Parameters
    switched = False
    original_regimen = regimen

    # Process data inputs
    drug_summary = drug_summary.sort_values('FIRST_SEEN')
    line_start_date = min(drug_summary['FIRST_SEEN'])

    # Check if any drugs in the drug summary table are eligible to be checked

    if input_drug_switch_ignore:
        # Get max last seen date from ineligible drugs, defined as drugs that don't occur after the 28 day regimen window
        ineligible_drugs = drug_summary[drug_summary['LAST_SEEN'] <= line_start_date + datetime.timedelta(days = input_r_window)]
        ineligible_drugs_last_seen = max(ineligible_drugs['LAST_SEEN'])
    
        # Get all the eligible drugs min first seen date. Eligible drugs are defined as drugs that occur after the 28 day regimen window
        eligible_drugs = drug_summary[drug_summary['LAST_SEEN'] > line_start_date + datetime.timedelta(days = input_r_window)]
        eligible_drugs_first_seen = min(eligible_drugs['FIRST_SEEN'])
        
    else: 
        # Get max last seen date from ineligible drugs
        ineligible_drugs = drug_summary[drug_summary['MED_NAME'].isin(cases) == False]
        
        ineligible_drugs_last_seen = max(ineligible_drugs['LAST_SEEN'])
        
        # Get all the eligible drugs min first seen date
        eligible_drugs = drug_summary[drug_summary["MED_NAME"].isin(cases)]
        if eligible_drugs.empty:
            eligible_drugs_first_seen = None
        else:
            eligible_drugs_first_seen = min(eligible_drugs['FIRST_SEEN'])

    if (eligible_drugs.empty == False) and (ineligible_drugs.empty == False):
        # If max last seen of an ineligible drug is before the min first seen of an eligible drug, then regimen is switched
        if ineligible_drugs_last_seen <= eligible_drugs_first_seen: 
            switched = True
  
    # If switch happened, then regimen is defined by eligible drugs list, otherwise it is from the original regimen
    if (switched):
        regimen = eligible_drugs['MED_NAME']
        line_start_date = min(eligible_drugs['FIRST_SEEN'])

    ## regimen = sapply(regimen, capitalize) -- do we need this line
    regimen = sorted(regimen)
    line_name = ','.join(regimen)
  
    return({'line_name':line_name, 'line_start':line_start_date, 'line_switched':switched})
        

###################################################################################
### Check Combo Dropped Drugs Function                                          ###
### This checks to see if combo dropped drugs should trigger a new line         ###
### Input: drug summary, line end date, line next start date, line end reason   ###
### Output: line name                                                           ###
### Python Version Copyright (c) 2020 Elena Samota, Merck Sharp & Dohme Corp.   ###
### a subsidiary of Merck & Co., Inc., Kenilworth, NJ, USA.                     ###
###################################################################################

def check_combo_dropped_drugs(drug_summary, line_end_date, line_next_start, line_end_reason):
    ## Get the list of dropped and undropped drugs
    undropped_drugs = drug_summary[drug_summary['DROPPED'] == 0]
    dropped_drugs = drug_summary[drug_summary['DROPPED'] == 1] 
    for ind in dropped_drugs.index: 
        line_end_date = min(dropped_drugs['LAST_SEEN'])
        line_next_start = line_end_date + datetime.timedelta(days = 1) # should I change this back to Elena's?
        # convert line_end_date to date, add one day, convert back to string
        #line_next_start = (((datetime.strptime(line_end_date, '%Y-%m-%d')).date()) + timedelta(days=1)).strftime('%Y-%m-%d')
        line_end_reason = "Combo drug dropped"
  
    return({'line_end_date' : line_end_date, 'line_next_start' : line_next_start, 'line_end_reason' : line_end_reason})



##################################################################################
### Is eligible drug substitution function                                     ###
### This checks for drug substitutions that do not advance the line of therapy ###
### Input: drug name, regimen, and list of special cases for substitutions     ###
### Output: True or False                                                      ###
### Python Version Copyright (c) 2020 Elena Samota,                            ###
### Merck Sharp & Dohme Corp. a subsidiary of Merck & Co., Inc.,               ###
### Kenilworth, NJ, USA.                                                       ###
##################################################################################

def is_eligible_drug_substitution (drug_name, regimen, cases_substitutions):

    drug_name = drug_name.upper()
    regimen = [r.upper() for r in regimen]
    
    # If regimen is in cases_substitutions original, then are there any of the corresponding 
    #substitutions containing the drug name? If not, return False
    return(cases_substitutions[cases_substitutions['original'].isin(regimen)]['substitute'].isin([drug_name]).any())




#############################################################################
### Is eligible drug addition function                                    ### 
### This checks for drug addition that do not advance the line of therapy ###
### Input: next drug name,and list of special cases for additions         ###
### Output: True or False                                                 ###
### Python Version Copyright (c) 2020 Sona Zalesakova,                    ###
### Merck Sharp & Dohme Corp. a subsidiary of Merck & Co., Inc.,          ###
### Kenilworth, NJ, USA.                                                  ###
#############################################################################

def is_eligible_drug_addition(drug_name, cases_additions):
    drug_name = drug_name.upper()
    return drug_name in cases_additions     


#############################################################################
### Is eligible mono/combo maintenance function                           ### 
### This checks to see if the line of therapy is a maintenance therapy    ###
### Input: regimen, line number, drug group (for combo), and list of      ###
### special cases for maintenance                                         ###
### Output: True or False                                                 ###
### Python Version Copyright (c) 2020 Sona Zalesakova,                    ###
### Merck Sharp & Dohme Corp. a subsidiary of Merck & Co., Inc.,          ###
### Kenilworth, NJ, USA.                                                  ###
#############################################################################

def is_eligible_switch_maintenance(regimen, cases_maintenance, line_number): 
    regimen = [x.upper() for x in regimen]    
    cases_maintenance = pd.DataFrame(data = cases_maintenance)
    cases_maintenance = cases_maintenance[cases_maintenance['maintenance_type'] == 'SWITCH']
    return all(drug in list(cases_maintenance['drug_name']) for drug in regimen) and (line_number == 1)


def is_eligible_continuation_maintenance(regimen, cases_maintenance, line_number, drug_group):  
 
    regimen = [x.upper() for x in regimen]
    
    drug_group = pd.DataFrame(data = drug_group)    
    drug_group = drug_group.apply(lambda x: x.astype(str).str.upper())    
    drug_group = drug_group[drug_group['MED_NAME'].isin(regimen)]    
    
    
    cases_maintenance = pd.DataFrame(data = cases_maintenance)
    cases_maintenance = cases_maintenance[cases_maintenance['maintenance_type']=='CONTINUATION']    
    cases_maintenance_set = set(cases_maintenance['drug_name'])    
    regimen_set = set(regimen)    
    intersect = list(regimen_set.intersection(cases_maintenance_set))

    #make sure we have existence of maintenance therapy drug
    if (len(intersect) == 0):
        return False
       
    # Check if the undropped drug is a maintenance drop
    # Step 1: Checked for undropped drugs and check that all undropped drugs are maintenance drugs
    # Step 2: Checked that there are at least 1 dropped drug
    # Step 3: Checked that not all the drugs are dropped
    elif (len(intersect) != 0):
        is_element = drug_group[drug_group['DROPPED'] == '0']
        is_element = (is_element['MED_NAME'])        
        is_element = all(drug in intersect for drug in is_element) 
        #!is.element(FALSE,drug_group$MED_NAME[drug_group$DROPPED==0] %in% intersect)
       
        
        drug_group_dropped_1 = drug_group[drug_group['DROPPED'] == '1']        
        drug_group_dropped_1 = drug_group_dropped_1['MED_NAME']       
        

        is_maintenance_therapy = is_element and (len(drug_group_dropped_1) >= 1) and (len(drug_group_dropped_1) < len(drug_group['MED_NAME']))       

        return(is_maintenance_therapy and (line_number == 0))     




##############################################################################################
### Is excluded from gap function                                                          ###
### This checks to see if the drug is eligible to be excluded from the discontinuation gap ###
### Input: Drug name and list of special cases for exclusions from discontinuation gap     ###
### Output: True or False                                                                  ###
### Python Version Copyright (c) 2020 Michal Hustak,                                       ###
### Merck Sharp & Dohme Corp.                                                              ###
### a subsidiary of Merck & Co., Inc., Kenilworth, NJ, USA.                                ###
##############################################################################################

def is_excluded_from_gap(regimen, remaining_drugs, cases_episode_gap):

    regimen = [x.upper() for x in regimen]
    exclude = False
    
    for index, row in remaining_drugs.iterrows():
        
        current_drug_name = (row['MED_NAME']).upper()

        if current_drug_name not in regimen:
            break
            
        elif current_drug_name in cases_episode_gap:
            exclude = True

    return(exclude)



###############################################################################
### Cut to first dose function                                              ###
### function snips the main dataframe (line.df) such that the first row     ###
### is always the first drug episode of the next line                       ###
### Inputs: 1) claims dataframe, 2) index_date (also serves as cut point),  ###
###         3) before window cut safezone, 4) after window cut safezone     ###
### Outputs: 1) claims dataframe                                            ###
### Python Version Copyright (c) 2020 Michal Hustak,                        ###
### Merck Sharp & Dohme Corp.                                               ###
### a subsidiary of Merck & Co., Inc., Kenilworth, NJ, USA.                 ###
###############################################################################


def snip_dataframe(df, cut_date):
    
    df_after = df[df['MED_START'] >= cut_date].reset_index(drop = True)
    df_before = df[df['MED_START'] < cut_date].reset_index(drop = True)

    ############# RETURN #############
    return({'after' : df_after, 'before' : df_before})


########################################################################
### Get Drug summary function                                        ###
### function summarizes patient drug dosage information in the line  ###
### Inputs: 1) claims dataframe, 2) line end date                    ###
### Outputs: drug summary dataframe                                  ###
### Python Version Copyright (c) 2020 Michal Hustak,                 ###
### Merck Sharp & Dohme Corp. a subsidiary of Merck & Co., Inc.,     ###
### Kenilworth, NJ, USA.                                             ###
########################################################################

def get_drug_summary(df, input_r_window, line_end_date):
    
    line_df = (df.loc[df['MED_START'] <= line_end_date]).sort_values(by = ['MED_START']).reset_index()
    #drug_summary = line_df.groupby(['MED_NAME']).agg(LAST_SEEN = ('MED_END', 'max'), FIRST_SEEN = ('MED_START', 'min')).reset_index(drop = True)
    drug_summary_last_seen = line_df.groupby('MED_NAME')['MED_END'].agg([('LAST_SEEN', 'max')]).reset_index()
    drug_summary_first_seen = line_df.groupby('MED_NAME')['MED_START'].agg([('FIRST_SEEN', 'min')]).reset_index()
    drug_summary = pd.merge(drug_summary_last_seen, drug_summary_first_seen, how = 'left', left_on = 'MED_NAME', right_on = 'MED_NAME')
    #drug_summary = drug_summary_0.groupby('MED_NAME')['MED_START'].agg([('FIRST_SEEN', 'max')])
    #drug_summary = line_df.groupby('MED_NAME')['MED_START'].agg([('FIRST_SEEN', 'max')])#.groupby('MED_NAME')['MED_START'].agg([('FIRST_SEEN', 'min')])
    #drug_summary = drug_summary.groupby('MED_NAME')['MED_START'].agg([('FIRST_SEEN', 'min')])
    #drug_summary = drug_summary.reset_index(drop = True)
    drug_summary['DROPPED'] = 0
    drug_summary.loc[(drug_summary['LAST_SEEN'] < line_end_date - timedelta(days = input_r_window)), 'DROPPED'] = 1  
    drug_summary['PATIENT_ID'] = line_df.loc[0, 'PATIENT_ID']
        
    return(drug_summary)
