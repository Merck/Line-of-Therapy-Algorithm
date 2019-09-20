#    Copyright (c) 2019 Merck Sharp & Dohme Corp. a subsidiary of Merck & Co., Inc., Kenilworth, NJ, USA.
#  
#    This file is part of the Line of Therapy Algorithm program.
#
#    Line of Theraphy Algorithm is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

##########################################################################
# rwToT_LoT_functions.R - Supporting script containing helper functions  #
# Authors: Weilin Meng, Wanmei Ou, Xin Chen, Wynona Black, Qian Xia      #
# Company: Merck (MSD), Center of Observational Research                 #
# Date Created: 2018-10-26                                               #
##########################################################################

library(dplyr)
library(Hmisc)

# This script contains functions that performs checks for special cases and exceptions in determining Line of Therapy:
# 1. check_line_name function checks for special cases to determine line name (i.e. If within 28 days patient switches to EGFR, ALK, PD-1/PD-L1, then regimen is called that)
# 2. is_eligible_drug_substitutions function checks for substitutions that do not advance line number (i.e. substitution of cisplatin for carboplatin and vice-versa)
# 3. is_eligible_drug_addition function checks for additions that do not advance the line number (i.e. Bevocizumab)
# 4. is_eligible_mono_maintenance and is_eligible_combo_maintenance checks for maintenance therapy eligibility (i.e. Pemetrexed, erlotinib and bevacizumab are eligible, depending on how they behave in mono/combo)
# 5. is_excluded_from_gap checks if line advancement should not occur after 120 days gap if it involves certain drugs

###############################################################
### Check Line Name Function                                ###
### This checks for special cases to determine line name    ###
### Input: regimen, drug summary, and list of special cases ###
### Output: line name                                       ###
###############################################################
check_line_name = function(regimen, drug_summary, cases) {
  # Parameters
  switched = FALSE
  original_regimen = regimen
  
  # Process data inputs
  drug_summary = drug_summary %>% arrange(FIRST_SEEN)
  line.start_date = min(drug_summary$FIRST_SEEN)
  
  # Check if any drugs in the drug summary table are eligible to be checked
  # Get max last seen date from ineligible drugs
  ineligible_drugs = drug_summary %>% filter(!MED_NAME %in% cases)
  ineligible_drugs_last_seen = max(ineligible_drugs$LAST_SEEN)
  # Get all the eligible drugs min first seen date
  eligible_drugs = drug_summary %>% filter(MED_NAME %in% cases)
  eligible_drugs_first_seen = min(eligible_drugs$FIRST_SEEN)
  
  if (nrow(eligible_drugs) > 0 & nrow(ineligible_drugs) > 0) {
    # If max last seen of an ineligible drug is before the min first seen of an eligible drug, then regimen is switched
    if (ineligible_drugs_last_seen < eligible_drugs_first_seen) {switched = TRUE}
  }
  
  # If switch happened, then regimen is defined by eligible drugs list, otherwise it is from the original regimen
  if (switched) {
    regimen = eligible_drugs %>% select(MED_NAME)
    line.start_date = min(eligible_drugs$FIRST_SEEN)
  }
  
  # Check if regimen and drugs in drug summary are equal
  #drug_summary = drug_summary %>% filter(LAST_SEEN > line.start_date + 28)
  #check_drugs = is.element(regimen,drug_summary$MED_NAME)
  
  # If not, then check if the FALSE drug is an eligible addition or substitution (which affects the line name)
  #if (is.element(FALSE,check_drugs)) {
  #  test = is.element(drug_summary$MED_NAME, regimen$MED_NAME)
  #  exclusion_index = which(FALSE == test)
    
  #  for (i in 1:length(exclusion_index)) {
  #    index = exclusion_index[i]
  #    drug_name = drug_summary$MED_NAME[index]
  #    drug_last_seen = drug_summary$LAST_SEEN[index]
      
  #    if (drug_last_seen <= line.start_date + 28) next
      # Check if it is an eligible addition
  #    if (is_eligible_drug_addition(drug_name, cases.line_additions)) {
  #      print("Note: Eligible drug addition found, adding to regimen and line name")
  #      print("Old information")
  #      print(drug_summary)
  #      print(regimen)
  #      regimen = c(regimen,drug_name)
  #      print("New information")
  #      print(regimen)
  #    }
      
      # Check if it is an eligible substitution
  #  }
  #}

  regimen = sapply(regimen, capitalize)
  regimen = sort(regimen)
  line.name = paste(regimen, collapse = ',')
  
  return(list("line_name" = line.name, "line_start" = line.start_date, "line_switched" = switched))
}


##################################################################################
### Is eligible drug substitution function                                     ###
### This checks for drug substitutions that do not advance the line of therapy ###
### Input: drug name, regimen, and list of special cases for substitutions     ###
### Output: True or False                                                      ###
##################################################################################
is_eligible_drug_substitution = function(drug_name, regimen, cases_substitutions) {
  drug_name = toupper(drug_name)
  regimen = sapply(regimen, toupper)

  # Is the regimen in the cases_substitutions original column? If not, return False
  # If regimen is in cases_substitutions original, then are any of the corresponding substitutions containing the drug name? If not, return False
  return(drug_name %in% cases_substitutions$substitute[cases_substitutions$original %in% regimen])
}

#############################################################################
### Is eligible drug addition function                                    ### 
### This checks for drug addition that do not advance the line of therapy ###
### Input: next drug name,and list of special cases for additions         ###
### Output: True or False                                                 ###
#############################################################################                                                                     ###
is_eligible_drug_addition = function(drug_name, cases_additions) {
  drug_name = toupper(drug_name)
  return(is.element(drug_name,cases_additions))
}


######################################################################################################
### Is eligible mono/combo maintenance function                                                    ### 
### This checks to see if the line of therapy is a maintenance therapy                             ###
### Input: regimen, line number, drug group (for combo), and list of special cases for maintenance ###
### Output: True or False                                                                          ###
######################################################################################################
is_maintenance = function(regimen, cases_maintenance, line_number, type) {
  regimen = sapply(regimen, toupper)
  cases_maintenance = as.data.frame(cases_maintenance) %>% filter(maintenance_type == type)
  return(is.element(regimen,cases_maintenance$drug_name) && line_number == 1)
}

is_eligible_continuation_maintenance = function(regimen, cases_maintenance, line_number, drug_group) {
  
  regimen = sapply(regimen, toupper)
  drug_group = as.data.frame(sapply(drug_group, toupper))
  drug_group = drug_group[drug_group$MED_NAME %in% regimen,]
  cases_maintenance = as.data.frame(cases_maintenance)
  intersect = intersect(regimen, cases_maintenance$drug_name)
  
  #make sure we have existence of maintenance therapy
  if(length(intersect) == 0) {return(FALSE)}
  
  is_maintenance_drug = is.element(0,drug_group$DROPPED[drug_group$MED_NAME %in% intersect])
  is_dropped_drug = (min(as.numeric(as.character(drug_group$DROPPED[!drug_group$MED_NAME %in% intersect]))) == 1)
  
  #make sure at least one maintenance drug is continued and one non-maintenance drug is dropped
  return(is_maintenance_drug && is_dropped_drug && line_number == 0)
}

##############################################################################################
### Is excluded from gap function                                                          ###
### This checks to see if the drug is eligible to be excluded from the discontinuation gap ###
### Input: Drug name and list of special cases for exclusions from discontinuation gap     ###
### Output: True or False                                                                  ###
##############################################################################################
is_excluded_from_gap = function(regimen, remaining_drugs, cases_episode_gap) {
  
  regimen = sapply(regimen, toupper)
  exclude = FALSE
  
  for(i in 1:nrow(remaining_drugs))
  {
    current_drug_name = toupper(remaining_drugs[i,'MED_NAME'])
    
    if (!is.element(current_drug_name,regimen)) {break}
    
    if(is.element(current_drug_name,cases_episode_gap)) {exclude = TRUE}
  }
  return(exclude)
}


###########################################################################################################################################
### Cut to first dose function                                                                                                          ###
### function snips the main dataframe (line.df) such that the first row is always the first drug episode of the next line               ###
### Inputs: 1) claims dataframe, 2) index_date (also serves as cut point), 3) before window cut safezone, 4) after window cut safezone  ###
### Outputs: 1) claims dataframe                                                                                                        ###
###########################################################################################################################################
cut_to_first_dose = function(df, cut_date, i_window_before, i_window_after) {
  remains = NULL
  
  #Scan through every row and remove it until one row's medication start date hits the defined window
  for(i in 1:nrow(df)) 
  {
    MED_START = df[i,'MED_START']
    MED_END = df[i,'MED_END']
    
    if (MED_START <= (cut_date+i_window_after) & MED_START >= (cut_date-i_window_before)) {
      found = TRUE
      if (i==1) {break}
      remains = unique(df[1:i-1,'MED_NAME'])
      df = df[-(1:i-1), ]
      break
    }
  }
  ############# RETURN #############
  return(list("df" = df, "remains" = remains))
}


###########################################################################################################################################
### Get Drug summary function                                                                                                           ###
### function summarizes patient drug dosage information in the line                                                                     ###
### Inputs: 1) claims dataframe, 2) line end date                                                                                       ###
### Outputs: drug summary dataframe                                                                                                     ###
###########################################################################################################################################
get_drug_summary = function(df, line.end_date) {
  
  line.df = df %>% filter(MED_START <= line.end_date) %>% arrange(MED_START)
  drug_summary = line.df %>% group_by(MED_NAME) %>% summarise(LAST_SEEN = max(MED_END), FIRST_SEEN = min(MED_START))
  drug_summary$DROPPED = 0
  drug_summary$DROPPED[line.end_date - drug_summary$LAST_SEEN > 21] = 1
  drug_summary$PATIENT_ID = line.df[1,'PATIENT_ID']
  
  ############# RETURN #############
  return(drug_summary)
}