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


###########################################################################
# rwToT_LoT_process.R - Main script to execute LoT business rules         #
# Authors: Weilin Meng, Wanmei Ou, Xin Chen, Wynona Black, Qian Xia       #
# Company: Merck (MSD), Center of Observational Research                  #
# Date Created: 2018-10-26                                                #
###########################################################################

library("rio")
library("dplyr")

#################################################################### General STEPS #########################################################################################################
# Input: Relevant claims data containing patient id, claims id, enrollment date/activity date, medication, and med start date
# Output: A master LoT list containing patient id, Line number, Line Name, Line start date, Line end date, line type, and line end reason
# 1. Create unique patient list to loop through
# 2. Loop through each patient in the patient list
# 3. For each patient, create a copy of the claims data filtered for only that patient
# 3. For that patient's claims data, order the data by ascending med start and grab line data on a step-wise line by line basis
# 4. Add the output to the LoT table
# 5. After grabbing each line data, cut the claims data to snip out the line information we already extracted so that the first line of the post-snipped data is the start of the new line
# 6. Repeat 3-5 until all lines for that patient is gathered. Then move to the next patient in the patient list until all patients are processed
############################################################################################################################################################################################


##################################
### hardcoded input parameters ###
##################################
input.r_window = 28
input.l_disgap = 120
input.indication = "NSCLC"
input.database = "Test"
input.filename = "test.csv"
input.outfile = "test"

source("rwToT_LoT_import.R")
source("rwToT_LoT_line.R")


##############################
### Load Preprocessed Data ### 
##############################
input.data = unique(as.data.frame(read.csv(paste("data/",input.indication,"/",input.database,"/",input.filename,sep=''), as.is= TRUE)))

input.unique_patients = unique(input.data$PATIENT_ID)

input.data$MED_START = as.Date(input.data$MED_START, format = "%Y-%m-%d")
input.data$MED_END = as.Date(input.data$MED_END, format = "%Y-%m-%d")
input.data$LAST_ACTIVITY_DATE = as.Date(input.data$LAST_ACTIVITY_DATE, format = "%Y-%m-%d")
input.data$LAST_ENROLLMENT_DATE = as.Date(input.data$LAST_ACTIVITY_DATE, format = "%Y-%m-%d")
input.data$FIRST_INDEX = as.Date(input.data$FIRST_INDEX, format = "%Y-%m-%d")
input.data$LAST_DOSE = as.Date(input.data$LAST_DOSE, format = "%Y-%m-%d")
input.data$MED_NAME = tolower(input.data$MED_NAME)

##################################################
### Blank template of final output to be saved ###
##################################################
output_lot = data.frame(PATIENT_ID=character(),
                    LINE_NUMBER = character(),
                    LINE_NAME = character(),
                    START_DATE = as.Date(character()),
                    END_DATE = as.Date(character()),
                    LINE_TYPE = character(),
                    IS_MAINTENANCE = logical(),
                    ADD_EXEMPTION = logical(),
                    SUB_EXEMPTION = logical(),
                    GAP_EXEMPTION = logical(),
                    NAME_EXEMPTION = logical(),
                    LAST_ACTIVITY_DATE = as.Date(character()),
                    LAST_ENROLLMENT_DATE = as.Date(character()),
                    LINE_END_REASON = character(),
                    ENHANCED_COHORT = character(),
                    INDEX_DATE = as.Date(character()),
                    stringsAsFactors=FALSE)

output_doses = data.frame(PATIENT_ID=character(),
                        MED_START = as.Date(character()),
                        MED_END = as.Date(character()),
                        MED_NAME = as.Date(character()),
                        LINE_NUMBER = character(),
                        LINE_NAME = character(),
                        stringsAsFactors=FALSE)

####################
### Script start ###
####################
# Loop through unique patients
for (i in 1:length(input.unique_patients)) {
  # Get data for that patient
  tmp.data = input.data %>% filter(PATIENT_ID == input.unique_patients[i])
  
  tmp.data = tmp.data %>% arrange(MED_START)
  input.index_date = tmp.data[1,'MED_START']
  input.last_activity_date = tmp.data[1,'LAST_ACTIVITY_DATE']
  input.last_enrollment_date = tmp.data[1,'LAST_ENROLLMENT_DATE']

  # Scan patient claims data to acquire line information on a step-wise line by line basis
  
  # Initialize the line number and other parameters to their initial values
  tmp.line_number = 0
  tmp.previous_line = NULL
  tmp.is_next_maintenance = FALSE

  # Scan through the patient's data until it is all through
  while (nrow(tmp.data)>0) {
    
    # Get Regimen and Line Start Information
    tmp.regimen = get_regimen(tmp.data, input.r_window)
    
    # Acquire rest of line data
    tmp.f_line_data = get_line_data(tmp.data, tmp.regimen, input.l_disgap, tmp.line_number, tmp.is_next_maintenance, input.r_window)
    tmp.line_name = tmp.f_line_data$line_name
    tmp.line_type = tmp.f_line_data$line_type
    tmp.line_start = tmp.f_line_data$line_start
    tmp.line_end = tmp.f_line_data$line_end
    tmp.line_next_start = tmp.f_line_data$line_next_start
    tmp.line_end_reason = tmp.f_line_data$line_end_reason
    tmp.line_number = tmp.f_line_data$line_number
    tmp.line_is_maintenance = tmp.f_line_data$line_is_maintenance
    tmp.is_next_maintenance = tmp.f_line_data$line_is_next_maintenance
    tmp.line_add_exemption = tmp.f_line_data$line_add_exemption
    tmp.line_sub_exemption = tmp.f_line_data$line_sub_exemption
    tmp.line_gap_exemption = tmp.f_line_data$line_gap_exemption
    tmp.line_name_exemption = tmp.f_line_data$line_name_exemption
    
    # Acquire dosage information associated with this line
    if (is.null(tmp.line_next_start) || is.na(tmp.line_next_start)) {
      tmp.output_doses = tmp.data
    } 
    else {
      tmp.output_doses = tmp.data %>% filter(MED_START < tmp.line_next_start)
    }
    
    # Append line data to final output 
    tmp.output_lot = data.frame("PATIENT_ID" = input.unique_patients[[i]],
                            "LINE_NUMBER" = tmp.line_number,
                            "LINE_NAME" = tmp.line_name,
                            "START_DATE" = tmp.line_start,
                            "END_DATE" = tmp.line_end,
                            "LINE_TYPE" = tmp.line_type,
                            "IS_MAINTENANCE" = tmp.line_is_maintenance,
                            "ADD_EXEMPTION" = tmp.line_add_exemption,
                            "SUB_EXEMPTION" = tmp.line_sub_exemption,
                            "GAP_EXEMPTION" = tmp.line_gap_exemption,
                            "NAME_EXEMPTION" = tmp.line_name_exemption,
                            "LAST_ACTIVITY_DATE" = input.last_activity_date,
                            "LAST_ENROLLMENT_DATE" = input.last_enrollment_date,
                            "LINE_END_REASON" = tmp.line_end_reason,
                            "ENHANCED_COHORT" = input.indication,
                            "INDEX_DATE" = input.index_date)
    
    output_lot = rbind(output_lot, tmp.output_lot)
    
    # Append patient dosage information w/ line information
    tmp.output_doses = tmp.output_doses %>% select(PATIENT_ID = PATIENT_ID, MED_START, MED_END, MED_NAME)
    tmp.output_doses$LINE_NUMBER = tmp.line_number
    tmp.output_doses$LINE_NAME = tmp.line_name
    tmp.output_doses$MED_NAME = sapply(tmp.output_doses$MED_NAME, capitalize)
    
    output_doses = rbind(output_doses, tmp.output_doses)

    tmp.previous_line = tmp.line_number
    
    # Cut the data to the next line
    if (is.null(tmp.line_next_start) || is.na(tmp.line_next_start)) {break}
    tmp.cut = snip_dataframe(tmp.data, tmp.line_next_start)
    tmp.data = tmp.cut$after
  }
}

write.csv(output_lot, file=paste("output/",input.indication,"/",input.database,"/output_lot_",input.outfile,".csv",sep=''), row.names=FALSE)
write.csv(output_doses, file=paste("output/",input.indication,"/",input.database,"/output_doses_",input.outfile,".csv",sep=''), row.names=FALSE)
write.csv(input.data, file=paste("output/",input.indication,"/",input.database,"/processed_input_",input.outfile,".csv",sep=''), row.names=FALSE)

