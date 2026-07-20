import os

def Log(config, *messages):

    logfile = config["LOG_FILE"]

    with open(logfile, "a") as f:
        
        for message in messages:
            f.write(str(message))
            f.write("\n")