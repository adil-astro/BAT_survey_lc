import os


def Load_Completed_Obsids(completed_file):
    
    completed_obsids = set()

    if not os.path.exists(completed_file):
        return completed_obsids
    
    with open(completed_file, "r") as f:
        
        for line in f:
            obsid = line.strip()

            if obsid:
                completed_obsids.add(obsid)
            
    return completed_obsids



def Save_Completed_Obsid(obsid, completed_file):

    with open(completed_file, "a") as f:
        f.write(f"{obsid}\n")


# def Search_Object(ra, dec):
    # Later modify to actually search the object by searching some database like simbad or vizier if user hasnt provided object name.
    # pass

