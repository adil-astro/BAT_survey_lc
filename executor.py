import os
import subprocess

from logger import Log

class NoGTIError(Exception):
    """Raised when a task completes but has no valid good time intervals."""
    pass



def Run_Command(config, task, cwd, env):

    name = task.name
    command = task.command

    output_path = os.path.join(cwd, task.expected_output)

    # delete the expected output file if it already exists.
    if os.path.exists(output_path):
        
        Log(config,
            f"Deleting {task.expected_output} file.\n")
        
        os.remove(output_path)

    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            env=env,
            check=True,
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL # Check if I really need this or not.
        )

        Log(config,
            f"\nTASK : {name}",
            f"COMMAND : {command}",
            "STATUS : SUCCESS",
            "STDOUT :",
            result.stdout,
            "STDERR :",
            result.stderr)


        stdout = result.stdout.lower()
        stderr   = result.stderr.lower()

        failure_strings = [
            "no overlapping good time intervals",
            "no good times were found",
        ]


        if any(s in stdout for s in failure_strings) or any(s in stderr for s in failure_strings):
            
            Log(config,
                "No valid GTIs found.")
            raise NoGTIError("No valid GTIs found.")
    
    except subprocess.CalledProcessError as e:

        Log(config,
            f"TASK : {name}",
            f"COMMAND : {command}",
            f"STATUS : FAILED ({e.returncode})",
            "STDOUT :",
            e.stdout,
            "STDERR :",
            e.stderr)

        raise


# ====================================================================================================
"""
Checks these things - 
1. Checks if the file exists or not.

"""
# ====================================================================================================

def Verify_Output(config, task, cwd):
    
    expected_output = task.expected_output

    output_path = os.path.join(cwd, expected_output)


    if os.path.exists(output_path):

        Log(config,
            f"OUTPUT EXISTS: {output_path}\n")
        
    else:
        Log(config,
            f"OUTPUT MISSING: {output_path}\n")

        raise FileNotFoundError(
            f"Expected output was not created:\n{output_path}")
    
