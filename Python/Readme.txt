Main Changes.

1.  Treatment cycles are added to the Line-of-Therapy determination.  

Cycle Definition:
  - Initial Treatment will be the start of the first cycle. 
  - Then, from the treatment day, look forward 4 days to see if another treatment is given.
  - Drug visits within the 4-day gap would be considered as the same cycle.   
  - A new cycle starts on the next drug administration date, once a 4-day gap is met. 
  - Each cycle will have a regimen defined based on the drug given. 
General Business Rules:
  - Allowable gap: l_disgap parameter 
  - If gap between administrations was greater than the allowable gap, advance the line
  - If gap between administrations was less than the allowable gap:
    - If a patient’s treatment changed (dropping something, switching to something new, or adding something new)…
        ... and the new combination had no new agents from the original (simply dropping something), do not advance the line
        ... and the new combination was different from the original therapy, or was the original therapy plus new agents, and the original therapy was given < 28 days, do not advance the line
        ... and the new combination was different from the original therapy, or was the original therapy plus new agents, and the original therapy was given for 2 cycles or 28+ days whichever is longer, advance the line

2.  Parallel processing is implemented

The input data frame is split into NS superchunks, each of these superchunks is split into NC chunks.  Superchunks are processed sequentially, but chunks within superchunk are processed in parallel.

The reason for this division is the following.

If the dataframe contains, for example, 3 million patients and 100 records per patient, this dataframe may be to big to process in parallel at one time.  We may want to split it into 10 superchunks, with 300,000 patients each.  Then every such superchunk can be split into 48 chunks and processed in parallel.  Once this superchunk is processed and the output LoT and doses are recorded, we can go to the next superchunk, until all the data from the original database is processed.

If the data frame is not too large, the NS parameter can be set to 1, and then the entire data set will be processed in parallel with 48 (or NC) processors at once.

