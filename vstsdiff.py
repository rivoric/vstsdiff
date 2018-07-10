from __future__ import print_function

import sys
import os
import base64
import json
import tempfile
import subprocess
import optparse
import requests

def _select_env (prompt, maxval, exclude=None):
    """Asks user for a number between 0 and maxval until they select a valid number.
    Optionally can also include a number that cannot be selected (used when asking for the second environment)."""
    full_prompt = "{0} between {1} and {2}".format(prompt,0,maxval)
    if exclude:
        full_prompt += " not including {0}".format(exclude)
    askforenv = True
    while askforenv:
        if sys.version_info[0] == 2:
            envstr = raw_input(full_prompt)
        else:
            envstr = input(full_prompt)
        try:
            envval = int(envstr)
        except:
            envval = -1
        askforenv = not (envval >= 0 and envval <= maxval and envval != exclude)
    return envval

def _write_env_file (obj, indent=2, name='tmp'):
    """Creates a temporary file and writes the passed obj out as a json document.
    Returns the name of the temporary file"""
    with tempfile.NamedTemporaryFile(mode='w',prefix=name.replace(' ','_'),delete=False) as envfile:
        json.dump(obj,envfile,indent=indent)
    return envfile.name

def _VSTS_header (username, PAT_token):
    """Returns a VSTS header dictionary to be used in API calls"""
    if sys.version_info[0] == 2:
        # Python 2
        headertoken = base64.b64encode("{0}:{1}".format(username, PAT_token))
        vstsheader = { 
            'Content-type': "application/json",
            'Authorization': "Basic {0}".format(headertoken)
        }
    else:
        # Python 3 or later
        headertoken = base64.b64encode("{0}:{1}".format(username, PAT_token).encode())
        vstsheader = { 
            'Content-type': "application/json",
            'Authorization': b"Basic " + headertoken
        }
    return vstsheader

def _get_diff_exe ():
    """Try a list of common comparison tools location to see if any exist"""
    difflist = [
        os.path.join(os.environ['ProgramFiles'],"Beyond Compare 4","BCompare.exe"),
        os.path.join(os.environ['ProgramFiles(x86)'],"Beyond Compare 4","BCompare.exe"),
        os.path.join(os.environ['ProgramW6432'],"Beyond Compare 4","BCompare.exe")
    ]

    bcfile = None
    for diffpath in difflist:
        if os.path.isfile(diffpath):
            bcfile = diffpath
            break
    return bcfile

def environment_files (username, PAT_token, account, project, release_definition, json_indent=2):
    """Use the VSTS API to get the release definition and then write the 2 selected envs to a file
    username = VSTS username (usually an email address)
    PAT_token = PAT token created in VSTS
    account = VSTS account name (account.visualstudio.com)
    project = VSTS project (visualstudio.com/project)
    release_definition = release definition name
    json_indent = number of spaces to indent each level of json document when saved
    returns 2 filenames (tuple)"""
    vstsheader = _VSTS_header(username,PAT_token)

    list_uri = "https://{0}.vsrm.visualstudio.com/{1}/_apis/release/definitions?api-version=4.1-preview.3".format(account,project)
    response = requests.get(list_uri,headers=vstsheader)
    if not response.ok:
        sys.exit(response.status_code)

    allreleasedefs = response.json()
    rdid = None
    for rd in allreleasedefs['value']:
        if rd['name'] == release_definition:
            rdid = rd['id']

    if rdid is None:
        # Not found the release defintion
        sys.exit(1)

    definition_uri = "https://{0}.vsrm.visualstudio.com/{1}/_apis/release/definitions/{2}?api-version=4.1-preview.3".format(account,project,rdid)
    response = requests.get(definition_uri,headers=vstsheader)
    if not response.ok:
        sys.exit(response.status_code)

    releasedef = response.json()
    numenvs = len(releasedef['environments'])
    if numenvs < 2:
        # no definitions or just 1 def
        sys.exit(2)
    elif numenvs == 2:
        # exactly 2, do comparision
        env1 = 0
        env2 = 1
    else:
        # more than 2 definitions, choose 2
        print('Select environments to compare')
        for indx, env in enumerate(releasedef['environments']):
            print(indx, ']', env['name'])
        env1 = _select_env("Select left environment for comparision",numenvs)
        env2 = _select_env("Select right environment for comparision",numenvs,env1)

    file1 = _write_env_file(releasedef['environments'][env1], indent=json_indent, name=releasedef['environments'][env1]['name'])
    file2 = _write_env_file(releasedef['environments'][env2], indent=json_indent, name=releasedef['environments'][env2]['name'])

    return file1, file2

def check_required_arguments(options, parser):
    """Checks that all options starting with [Required] have been included
    Taken from Fausto Luiz Santin answer to SO 4407539"""
    missing_options = []
    for option in parser.option_list:
        if option.help.startswith('[Required]') and eval('options.' + option.dest) == None:
            missing_options.extend(option._long_opts)
    if len(missing_options) > 0:
        print('Missing REQUIRED parameters: ' + str(missing_options))
        parser.parse_args(['-h'])

if __name__ == "__main__":
    parser = optparse.OptionParser()
    parser.add_option('-u','--username', action="store", dest="user",
                      help="[Required] Username (usually email address) of VSTS account")
    parser.add_option('-t','--pat', action="store", dest="pat",
                      help="[Required] VSTS Personal Access Token, PAT, to connect with")
    parser.add_option('-a','--account', action="store", dest="acc",
                      help="[Required] VSTS account name")
    parser.add_option('-r','--release-definition', action="store", dest="rd",
                      help="[Required] Username (usually email address) of VSTS account")
    parser.add_option('-p','--project', action="store", dest="proj",
                      help="[Required] VSTS project name")
    parser.add_option('-c','--compare-exe', action="store", dest="bc",
                      help="[Optional] Path to the comparison program, defaults to Beyond Compare 4 in default location")
    parser.add_option('-i','--indent', action="store", type="int", dest="indent", default=2,
                      help="[Optional] Number of spaces to indent the json file, defaults to 2")
    parser.add_option('-d','--delete-temp-files', dest="deltmp", default = False, action = 'store_true',
                      help="[Optional] Delete the temp files on exit")
    options, additional_args = parser.parse_args()
    check_required_arguments(options, parser)

    envfile1, envfile2 = environment_files(
        username=options.user,
        PAT_token=options.pat,
        account=options.acc,
        project=options.proj,
        release_definition=options.rd,
        json_indent=options.indent
    )

    if options.bc:
        bcexe = options.bc
    else:
        bcexe = _get_diff_exe()
        if bcexe is None:
            sys.exit(3)

    commandline = [ bcexe, envfile1, envfile2 ]
    subprocess.call(commandline)
    if options.deltmp:
        os.unlink(envfile1)
        os.unlink(envfile2)
