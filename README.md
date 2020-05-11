# Line of Therapy Algorithm

This is the Line of Therapy Algorithm, as described in the paper "Temporal phenotyping by mining healthcare data to derive lines of therapy for cancer" accepted in the Journal of Biomedical Informatics." https://www.ncbi.nlm.nih.gov/pubmed/31689549

Authors: Weilin Meng, Wanmei Ou, Wynona Black, Xin Chen, Sheenu Chandwani, Zhaohui Cai

Copyright© 2019 Merck Sharp & Dohme Corp. a subsidiary of Merck & Co., Inc., Kenilworth, NJ, USA.

Last updated: 05/11/2020

##### NOTE: If there is interest in contributing to the algorithm, then please contact Weilin Meng (weilin.meng@merck.com)


## Introduction

The purpose of having line of therapy rules is to determine the start date, end date, line number and treatment regimen of a patient’s journey toward treating cancer. Typically, this information is not available in an EHR or claims database, but is rather derived from medication history information via business rules. EHR databases most commonly have rules deriving line of therapy due to their availability of medical chart reviews. Claims do not have this information, and therefore special rules and considerations need to be applied when deriving line of therapy information.

Merck has internally developed business rules to take patient drug claims administrations and convert them into line of therapy treatment patterns for the purpose of performing downstream analysis such as oncology time on treatment analysis. At this moment the Line of Therapy Algorithm is supported for NSCLC, Melanoma and HNSCC indications Oncology indications.

There are five common parameters that define line of therapy rules:
1. Index Date Definition – Defining the index date defines when 1L treatment and first drug episode occurs
2. 1L first drug episode – Defining when first drug episode occurs and what drugs are eligible to be included in 1L treatment will pave the way for the definition of subsequent lines
3. Line Regimen Defining Window – This window defines the line treatment regimen (combo or mono therapy). Drugs that are administered within this window (the window typically starts from the first drug episode for that line number) are included in the treatment regimen definition.
4. New Drug Line Advancement – Typically a new drug that is administered outside the treatment regimen will advance the patient to a new line. However, the exact rules that define this behavior may differ between indication
5. Gaps in Therapy Window – Typically if there is a large gap in drug administered, then that will trigger the end of the current line and start of the next line.

However, depending on the indication of interest, these five common parameters are not entirely comprehensive or have exceptions. The Line of Thereapy Algorithm is an in-depth execution of these parameters, designed to allow for modifications of these parameters.

## Requirements for R
* R (>= 3.5.1) 
* R packages: dplyr, Hmisc, rio

## Requirements for Python
* Python (>= 3.7)
* Python libraries: pandas

## Install
Clone or Download from github

## Getting Started

##### NOTE: The Line of Therapy Algorithm is not responsible for cohort selection or eligible drug selection. This pre-processing step should be done by the user before any input to the algorithm **

##### NOTE: The doucmentation is written in the perspective of R. However, the Python version is coded similarily to the R version and so the documentation here should suffice **

To use the code:
1. Open rwToT_LOT_main.R
2. The file will contain several parameters that can be altered:

```
input.r_window = 28  # Threshold number of days for the regimen defining window to detect combination drugs
input.l_disgap = 180 # Threshold number of days of gap in administration before advancing the line
input.drug_switch_ignore = FALSE  # Flag to see if a drug is administered during the r_window period, but never administered again after, then ignore it from the regimen. 
input.combo_dropped_line_advance = FALSE  # Flag to see if a combination drug is dropped, whether or not it triggers an advance in ine number.
input.indication = "NSCLC"  # The indication of interest, which also points to the appropriate "NSCLC" folder
input.database = "Test"  # The folder specifying the data location within the above indication folder
input.filename = "example_input.csv"  # The file name containing the input data
input.outfile = "test". # The output file name
```

3. Make sure your input file is of the same format as "example_input.csv" in the data/NSCLC/test/ folder
4. Edit or alter any of the files in the "reference" folder (see Overview section for more details) that pertain to your use case.
5. Run the script. After the run is complete, you should see your output LOT in your output/{indication}/{database}/ folder

## Overview
The LOT code consists of primarily four R script files as well as six reference CSV files. The four script files either run the main execution of the line of therapy calculation, or contain supporting functions that the main execution calls on. 

The six reference CSV files contain indication specific information on drugs that have special exemption properties (drug additions, substitutions, maintenance therapy, gaps in therapy, etc) or contain a mapping to standardize drug names and exclude certain drugs from the calculation. These CSV files are imported in the beginning of the execution and referenced throughout. It is these CSV files that will contain information that differentiates the rules on an indication basis. Therefore, the CSV files for NSCLC will contain different information that the files for Melanoma or HNSCC.

The R script file list is as below:
* rwToT_LoT_main.R – the main script that takes the input and produces LoT output
* rwToT_LoT_line.R – A script containing functions that extract line of therapy and regimen information
* rwToT_LoT_import.R – An import script importing reference CSV files containing indication specific fields, variables, exclusions, etc.
* rwToT_LoT_functions.R – A script containing a collection of helper functions and functions that check for special cases, maintenance therapy, etc for line of therapy.


The reference folder contains reference CSV files that are imported via rwToT_LoT_import.R as below:
* Cases_addition.csv – a list of drugs that are exempt from line advancement when introduced outside the regimen period
* Cases_episode_gap.csv – a list of drugs that are exempt form gaps in administration that would otherwise advance the line
* Cases_line_name.csv – a list of drugs that, when switched to during the regimen defining period, will initiate a switch in treatment regimen (ignoring the previous drug that was switched out)
* Cases_maintenance.csv – a list of drugs that are eligible to make the therapy called a maintenance therapy
* Cases_substitutions.csv – a list of drugs that are exempt from line advancement when it is substituted to another, usually similar, drug.
* Ref_med_name.csv – a csv list that contains drug name mappings to a standardized drug naming convention, and also contains indicators to know when a drug should be excluded from the line of therapy business rule implementation.


#### rwToT_LoT_main.R
This script is the main execution script that takes the input data, calls on functions from other R scripts to calculate line information, and produces the line of therapy output.

The relevant line information the execution will extract are as below:
* Line name
* Line type (mono, combo therapy)
* Line start date
* Line end date
* Line next Start (start date of the next line, if applicable)
* Line number
* Line end reason (debugging information to see why the line has ended)
* Line is Maintenance (a flag to indicate if the line if a maintenance therapy)
* Line Treatment Naïve (a flag to indicate if previous regimen history was detected prior to the patient’s first index drug administration)
* Flag for if drug addition exemption rule is triggered
* Flag for if drug substitution exemption rule is triggered
* Flag for if drug episode gap exemption rule is triggered
* Flag for if regimen switch rule is triggered


The script initial hardcoded parameters are:
* Input.r_window - The regimen defining window
* Input.l_disgap - The maximum gap in therapy window
* Input.indication – The indication (e.g. NSCLC, MELANOMA, HNSCC)
* Input.database – The database name (Optum, Truven, etc)


#### rwToT_LoT_line.R
This script contains two functions necessary to calculate necessary line of therapy information:
1. get_regimen function returns the eligible drugs in a regimen, defined as drugs within a window (28 days) relative to the first drug episode
2. get_line_data function returns relevant line of therapy information such as line name, line end date, is maintenance therapy, next line start date, line type, and line end reason, etc.


#### rwToT_LoT_functions.R
This script contains functions that perform checks on special exemptions, exclusions, and exceptions to the line of therapy business rules as well as helper functions that aid in data manipulation and labeling.

