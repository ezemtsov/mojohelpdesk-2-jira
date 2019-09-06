# mojo2jira


<a id="org05c4b30"></a>

## export your MOJO Helpdesk ticket data in jira-friendly CSV format with comments


<a id="org79a7be8"></a>

## How to use

python3 mojo2jira.py -k {YOUR API KEY} -q {MOJO QUEUE ID}

Successfull execution results in ticketData.csv file in same folder

Following options are available:
    -k {YOUR API KEY}
    -q {MOJO QUEUE ID}
    -c {MAX COMMENTS PER TICKET}


<a id="org1f7ae43"></a>

## Notes

-   Export progress is saved on disk, so that it can be continued on failure.
-   On start script creates ticketQueue.json file with all tickets to be exported.
-   Don't forget to delete ticketQueue.json file if you need to start a new export.
-   HTTP requests are executed in batches of 24 requests. This can be corrected if needed.

