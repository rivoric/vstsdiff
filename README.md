VSTS Diff
---------

The inspiration for this utility came about because I needed to check the settings on the tasks for two release environments were the same.
You can export the definition and then copy the relevant environments out into files to then compare then,
but as the export is available from the API this is a job ideally suited to Python.


Installation
------------

Just copy the python script vstsdiff.py locally and run pip install -r requirements.txt