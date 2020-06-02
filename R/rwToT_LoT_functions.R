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
# 2. check_combo_dropped_drugs checks to see if we should advance to a new line if a drug in a combo regimen is dropped
# 3. is_eligible_drug_substitutions function checks for substitutions that do not advance line number (i.e. substitution of cisplatin for carboplatin and vice-versa)
# 4. is_eligible_drug_addition function checks for additions that do not advance the line number (i.e. Bevocizumab)
# 5. is_eligible_mono_maintenance and is_eligible_combo_maintenance checks for maintenance therapy eligibility (i.e. Pemetrexed, erlotinib and bevacizumab are eligible, depending on how they behave in mono/combo)
# 6. is_excluded_from_gap checks if line advancement should not occur after 120 days gap if it involves certain drugs

###############################################################
### Check Line Name Function                                ###
### This checks for special cases to determine line name    ###
### Input: regimen, drug summary, and list of special cases ###
### Output: line name                                       ###
###############################################################
check_line_name = function(regimen, drug_summary, cases,  input.r_window, input.drug_switch_ignore) {
  # Parameters
  switched = FALSE
  original_regimen = regimen
  
  # Process data inputs
  drug_summary = drug_summary %>% arrange(FIRST_SEEN)
  line.start_date = min(drug_summary$FIRST_SEEN)
  
  # Check if any drugs in the drug summary table are eligible to be checked

  if (input.drug_switch_ignore) {
    # Get max last seen date from ineligible drugs, defined as drugs that don't occur after regimen window threshold
    ineligible_drugs = drug_summary %>% filter(LAST_SEEN <= line.start_date+input.r_window)
    ineligible_drugs_last_seen = max(ineligible_drugs$LAST_SEEN)
    
    # Get all the eligible drugs min first seen date. Eligible drugs are defined as drugs that occur after the regimen window threshold
    eligible_drugs = drug_summary %>% filter(LAST_SEEN > line.start_date+input.r_window)
    eligible_drugs_first_seen = min(eligible_drugs$FIRST_SEEN)
  } else {
    # Get max last seen date from ineligible drugs
    ineligible_drugs = drug_summary %>% filter(!MED_NAME %in% cases)
    ineligible_drugs_last_seen = max(ineligible_drugs$LAST_SEEN)
    # Get all the eligible drugs min first seen date
    eligible_drugs = drug_summary %>% filter(MED_NAME %in% cases)
    eligible_drugs_first_seen = min(eligible_drugs$FIRST_SEEN)
  }

  
  if (nrow(eligible_drugs) > 0 & nrow(ineligible_drugs) > 0) {
    # If max last seen of an ineligible drug is before the min first seen of an eligible drug, then regimen is switched
    if (ineligible_drugs_last_seen <= eligible_drugs_first_seen) {switched = TRUE}
  }
  
  # If switch happened, then regimen is defined by eligible drugs list, otherwise it is from the original regimen
  if (switched) {
    regimen = eligible_drugs %>% select(MED_NAME)
    line.start_date = min(eligible_drugs$FIRST_SEEN)
  }

  regimen = sapply(regimen, capitalize)
  regimen = sort(regimen)
  line.name = paste(regimen, collapse = ',')
  
  return(list("line_name" = line.name, "line_start" = line.start_date, "line_switched" = switched))
}

###################################################################################
### Check Combo Dropped Drugs Function                                          ###
### This checks to see if combo dropped drugs should trigger a new line         ###
### Input: drug summary, line end date, line next start date, line end reason   ###
### Output: line name                                                           ###
###################################################################################
check_combo_dropped_drugs = function(drug_summary, line.end_date, line.next_start, line.end_reason) {
  # Get the list of dropped and undropped drugs
  undropped_drugs = drug_summary %>% filter(DROPPED == 0)
  dropped_drugs = drug_summary %>% filter(DROPPED == 1)
  
  if (nrow(dropped_drugs) > 0) {
    line.end_date = min(dropped_drugs$LAST_SEEN)
    line.next_start = line.end_date + 1
    line.end_reason = "Combo drug dropped"
  }
  
  return(list("line_end_date" = line.end_date, "line_next_start" = line.next_start, "line_end_reason" = line.end_reason))
  
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
is_eligible_switch_maintenance = function(regimen, cases_maintenance, line_number) {
  regimen = sapply(regimen, toupper)
  cases_maintenance = as.data.frame(cases_maintenance) %>% filter(maintenance_type == "SWITCH")
  return(!is.element(FALSE,regimen %in% cases_maintenance$drug_name) && line_number == 1)
}

is_eligible_continuation_maintenance = function(regimen, cases_maintenance, line_number, drug_group) {
  regimen = sapply(regimen, toupper)
  drug_group = as.data.frame(sapply(drug_group, toupper))
  drug_group = drug_group[drug_group$MED_NAME %in% regimen,]
  cases_maintenance = as.data.frame(cases_maintenance) %>% filter(maintenance_type == "CONTINUATION")
  intersect = intersect(regimen, cases_maintenance$drug_name)
  
  #make sure we have existence of maintenance therapy drug
  if(length(intersect) == 0) {return(FALSE)}
  
  # Check if the undropped drug is a maintenance drop
  # Step 1: Checked for undropped drugs and check that all undropped drugs are maintenance drugs
  # Step 2: Checked that there are at least 1 dropped drug
  # Step 3: Checked that not all the drugs are dropped
  is_maintenance_therapy = !is.element(FALSE,drug_group$MED_NAME[drug_group$DROPPED==0] %in% intersect) && 
                            length(drug_group$MED_NAME[drug_group$DROPPED==1]) >= 1 &&
                            length(drug_group$MED_NAME[drug_group$DROPPED==1]) < length(drug_group$MED_NAME)

  #make sure at least one maintenance drug is continued and all non-maintenance drug is dropped
  return(is_maintenance_therapy && line_number == 0)
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
snip_dataframe = function(df, cut_date) {

  df_after = df %>% filter(MED_START >= cut_date)
  df_before = df %>% filter(MED_START < cut_date)

  ############# RETURN #############
  return(list("after" = df_after, "before" = df_before))
}


###########################################################################################################################################
### Get Drug summary function                                                                                                           ###
### function summarizes patient drug dosage information in the line                                                                     ###
### Inputs: 1) claims dataframe, 2) line end date                                                                                       ###
### Outputs: drug summary dataframe                                                                                                     ###
###########################################################################################################################################
get_drug_summary = function(df, input.r_window, line.end_date) {
  
  line.df = df %>% filter(MED_START <= line.end_date) %>% arrange(MED_START)
  drug_summary = line.df %>% group_by(MED_NAME) %>% summarise(LAST_SEEN = max(MED_END), FIRST_SEEN = min(MED_START))
  drug_summary$DROPPED = 0
  drug_summary$DROPPED[line.end_date - drug_summary$LAST_SEEN > input.r_window] = 1
  drug_summary$PATIENT_ID = line.df[1,'PATIENT_ID']
  
  ############# RETURN #############
  return(drug_summary)
}