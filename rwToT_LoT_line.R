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

#####################################################################################
# rwToT_LoT_line_NSCLC.R - Supporting script containing NSCLC LoT related functions #
# Authors: Weilin Meng, Wanmei Ou, Xin Chen, Wynona Black, Qian Xia                 #
# Company: Merck (MSD), Center of Observational Research                            #
# Date Created: 2018-10-26                                                          #
#####################################################################################

library(dplyr)
library(lubridate)
source("rwToT_LoT_functions.R")

# This script contains a collection of functions necessary to compute a proper line of therapy:
# 1. get_regimen function returns the eligible drugs in a regimen, defined as drugs within a window relative to the first episode
# 2. get_line_data function returns relevant line of therapy information such as line name, line end date, is maintenance therapy, next line start date, line type, and line end reason


#########################################################################################################################
### Get Regimen Function                                                                                              ###
### function: returns the eligible drugs in a regimen, defined as drugs within a window relative to the first episode ###
### Inputs: 1) claims dataframe, 2) regimen defining window (days) 3) line number                                     ###
### Outputs: 1) list of drugs in the regimen, 2) line start date                                                      ###
#########################################################################################################################
get_regimen = function(df, r_window) {
  
  # Start of line from the first row, which is assumed to be first drug epsiode (accomplished via cut_to_first_dose function)
  # Later in the code/process, this line start is double checked and challenged if there is an eligible drug switch
  tmp.line_start = df[1,'MED_START']
  # Set the regimen window relative to the line start
  regimen_end_date = tmp.line_start + r_window
  
  # Take the line start date, then project to regimen defining window, and get unique list of medications
  tmp.regimen = df %>% filter(MED_START <= regimen_end_date) 
  output.regimen = unique(tmp.regimen$MED_NAME)
  
  ############# RETURN #############
  return(output.regimen)
}

############################################################################################################################################################################
### Get Line Data Function                                                                                                                                               ###
### function returns relevant line of therapy information such as line name, line end date, is maintenance therapy, next line start date, line type, and line end reason ###
### Inputs: 1) claims dataframe, 2) regimen, 3) discontinuation gap (days), 4) line number                                                                               ###
### Outputs: 1) line name, 2) line end date, 3) next line start date, 4) line type, 5) line end reason, 6) is maintenance therapy                                        ###
### General Steps:                                                                                                                                                       ###
### 1. Check if we hit last row of table - if so then there is no further data to analyze and we stop here, setting end date to be the last date activity                ###
### 2. Check if there is a gap between the current drug date for that line. If there is, then we move to the second pass of checks                                       ###
### 3. Check if the the next drug is a drug not within the regimen. If there is, then we move to the second pass of checks                                               ###
### 4. Second pass - analyze combo treatment and determine the correct discontinuation date and account for drug introduction                                            ###
### 5. Second pass - analyze the discontinuations and account for exceptions to discontinuations based on medication                                                     ###
### 6. Second pass- analyze if the treatment is maintenance therapy. If it is, then label it as such and do not advance line number                                      ###
### 7. Compute final outputs and return it                                                                                                                               ###
############################################################################################################################################################################
get_line_data = function(df, r_regimen, l_disgap, l_line_number, l_is_next_maintenance, input.r_window) {
  # Set assumptions
  line.is_maintenance = FALSE
  line.type = ifelse(length(r_regimen) > 1,"combo","mono")
  line.line_number = l_line_number
  line.line_start = NULL
  line.is_next_maintenance = l_is_next_maintenance
  
  has_eligible_drug_addition = FALSE
  has_eligible_drug_substition = FALSE
  has_gap_exemption = FALSE
  has_line_name_exemption = FALSE
  
  ############### First Pass Checks #################
  # If we hit the last row in the claims database, then stop and return outputs
  if (1 == nrow(df)) {
    line.end_date = df[1,'MED_END']
    line.end_reason = "Last row hit"
    line.next_start = NULL
  }
  # Scan all rows in the claims database and grab information on the  current drug and the next drug in the timeline
  else {
    for(i in 2:nrow(df)) {
      # Grab information on current drug and next drug
      current.drug = df[i-1,'MED_NAME']
      current.drug_date = df[i-1,'MED_START']
      current.drug_end = df[i-1,'MED_END']
      next.drug = df[i,'MED_NAME']
      next.drug_date = df[i,'MED_START']
      remaining.drugs = df[i:nrow(df),]
      has_eligible_drug_addition = is_eligible_drug_addition(next.drug, cases.line_additions)
      has_eligible_drug_substition = is_eligible_drug_substitution(next.drug, r_regimen, cases.line_substitutions)
      has_gap_exemption = is_excluded_from_gap(r_regimen, remaining.drugs, cases.episode_gap)
      
      # If you hit the last row in the scan, then stop and return outputs
      if (i == nrow(df) && (is.element(next.drug, r_regimen) || has_eligible_drug_substition || has_eligible_drug_addition)) {
        if (next.drug_date - current.drug_end > l_disgap && !has_gap_exemption) {
            line.end_date = current.drug_end
            line.end_reason = "Passed discontinuation gap"
            line.next_start = next.drug_date
        }
        else {
          line.end_date = df[i,'MED_END']
          line.end_reason = "Last row hit"
          line.next_start = NULL
        }

        break
      }
      # Check if the gap between the next drug and current drug is wider than the discontinuation gap
      else if (next.drug_date - current.drug_end > l_disgap) {
        # If drug is excluded from the discontinuation gap, then skip whole process and go to the next drug
        if (has_gap_exemption) {next}
        line.end_date = current.drug_end
        line.end_reason = "Passed discontinuation gap"
        line.next_start = next.drug_date
        break
      }
      # Check if the next drug is not part of the regimen
      else if (!is.element(next.drug, r_regimen) && !has_eligible_drug_addition && !has_eligible_drug_substition){
        line.end_date = current.drug_end
        line.end_reason = "New line started with new drugs"
        line.next_start = next.drug_date

        break
      }
    }
  } # End first pass of checks
  
  
  ################### Second pass on combo treatment to detect supressions and gaps ###################
  
  # Get Drug Summary information
  line.drug_summary = get_drug_summary(df, input.r_window, line.end_date)
  
  # Re-compute line name and line start date
  check_line_name = check_line_name(r_regimen, line.drug_summary, cases.line_name)
  line.name = check_line_name$line_name
  line.line_start = check_line_name$line_start
  has_line_name_exemption = check_line_name$line_switched
  
  
  # Compute Line Type
  tmp.line_regimen = strsplit(line.name,',')[[1]]
  line.type = ifelse(length(tmp.line_regimen) == 1,"mono","combo")
  

  # Check to see if the current line is maintenance therapy
  if (line.line_number == 1) {
    if (line.is_next_maintenance) {
      line.is_maintenance = TRUE
    }
    else {
      line.is_maintenance = is_eligible_switch_maintenance(r_regimen, cases.line_maintenance, line.line_number)
    }
    line.is_next_maintenance = FALSE
  }
  # Check for continuation maintenance therapy within the combo treatment
  else if (line.type == "combo" && line.line_number == 0) {

    line.is_next_maintenance = is_eligible_continuation_maintenance(r_regimen, cases.line_maintenance, line.line_number, line.drug_summary)

    # If the line is eligible for maintenance and is combo, then split it
    if (line.is_next_maintenance) {
      tmp.drug_group_dropped = line.drug_summary %>% filter(DROPPED == 1)
      line.next_start = as.Date(max(tmp.drug_group_dropped$LAST_SEEN), format = "%Y-%m-%d") + input.r_window
      line.end_reason = "Entering continuation maintenance therapy"
    }
  }
  
  ########### Compute remaining final outputs ############
  if (!line.is_maintenance) {line.line_number = line.line_number + 1}

  ############# RETURN #############
  return(list("line_name" = line.name, 
              "line_type" = line.type, 
              "line_start" = line.line_start, 
              "line_end" = line.end_date, 
              "line_next_start" = line.next_start, 
              "line_end_reason" = line.end_reason, 
              "line_number" = line.line_number, 
              "line_is_maintenance" = line.is_maintenance, 
              "line_is_next_maintenance" = line.is_next_maintenance,
              "line_add_exemption" = has_eligible_drug_addition,
              "line_sub_exemption" = has_eligible_drug_substition,
              "line_gap_exemption" = has_gap_exemption,
              "line_name_exemption" = has_line_name_exemption))
  
}

