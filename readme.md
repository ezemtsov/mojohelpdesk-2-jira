# mojo2jira


<a id="org05c4b30"></a>

## export your MOJO Helpdesk ticket data in jira-friendly CSV format with comments


<a id="org79a7be8"></a>

## How to use
```
python3 mojo2jira.py --key {YOUR API KEY} --id {MOJO QUEUE/GROUP ID} --mode {QUEUE || GROUP}
```
Successfull execution results in ticketData.csv file in same folder

Following options are available:
```
--key {YOUR API KEY} (mandatory)
--id {MOJO GROUP/QUEUE ID} (mandatory)
--mode {GROUP || QUEUE} (mandatory)
--max_comments {MAX COMMENTS PER TICKET}
```
<a id="org1f7ae43"></a>

## Dependencies
```
pip3 install requests
```
## Notes

-   Export progress is saved on disk, so that it can be continued on failure.
-   On start script creates ticketQueue.json file with all tickets to be exported.
-   Don't forget to delete ticketQueue.json file if you need to start a new export.
-   HTTP requests are executed in batches of 24 requests. This can be corrected if needed.

