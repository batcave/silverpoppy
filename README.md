SilverPoppy
===========
A minimal API library for the Engage Silverpop mailing list management system.

Dependencies
------------
Right now there is a dependency on lxml and this is not set to auto-install during pip install, deferring to user preferences on this. (STATIC_DEPS, etc.)

See: http://lxml.de/installation.html

Installation
------------
This is packaged as a pip install.
```
pip install -e git+git://github.com/kevinwaddle/silverpoppy.git#egg=silveroppy
```

Usage
-----
Import the module:
```
from silverpoppy import Engage
```

Instantiate an Engage() object, providing the api_url for your account's pod:
```
api_url = 'http://api1.silverpop.com/XMLAPI'
eng = Engage(api_url)
```

Then login:
```
eng.login(username='yourusername', password='the_password')
```

Optionally provide an ftp_url if you are going to be using calls that require files to be ftp'd in and out of your Engage account:
```
eng.ftp_address = 'transfer1.silverpop.com'
```
Engage.ftp_putfile(filename) and Engage.ftp_putfile(filename, outfilepath) are provided for managing sending and retrieving files that some API Calls require.

Consult the Engage API documentation for more details on these requirements.

The main call is through xml_engage_request(), providing a valid xml document for the given Engage API call.

An EngageResponse() object is returned.

```
xml_purge_contact = """
<Envelope>
    <Body>
        <RemoveRecipient>
            <LIST_ID>{0}</LIST_ID>
            <EMAIL>{1}</EMAIL>
        </RemoveRecipient>
    </Body>
</Envelope>
""".format('123456', 'username@domain.com')

resp = eng.xml_engage_request(xml_purge_contact)

# Check the response object for success...
if resp.SUCCESS:
   ...
```

The EngageResponse() object can handle resulting jobs if the Engage API Call generates one.

EngageResponse.handle_job() will synchronously check the job status every 5 seconds logging the status and returning when the job completes or fails.
```
resp.handle_job()

#results to log/stdout....
2013-11-25 12:00:38,561 | INFO - ImportList: API called, JOB_ID: 23573474
2013-11-25 12:00:38,678 | INFO - ImportList: JOB_ID: 23573474, STATUS: WAITING
2013-11-25 12:00:43,875 | INFO - ImportList: JOB_ID: 23573474, STATUS: COMPLETE
```

Or you can call EngageResponse.get_job_status() manually to check the status of a job.
```
job_state = resp.get_job_status()
print job_state

WAITING
```

You can also get a value out of a resulting response for an item with the EngageResponse.result(item) call.
```
xml_getlistmetadata = """
<Envelope>
    <Body>
        <GetListMetaData>
            <LIST_ID>{0}</LIST_ID>
        </GetListMetaData>
    </Body>
</Envelope>
""".format('123456')

resp = Engage.xml_engage_request(xml_getlistmetadata)

if resp.SUCCESS:
    if int(resp.result('SIZE')) == 0:
        ...
```
