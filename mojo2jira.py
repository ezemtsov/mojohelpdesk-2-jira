import sys
import csv
import datetime

from concurrent.futures import ThreadPoolExecutor as PoolExecutor
import requests

# Simple HTTP get call
def get(url):
    res = requests.get(url, headers=headers, timeout=2)
    return res.json()

# Concurrent get requests
def parallelGet(urls):
    with PoolExecutor(max_workers=parallelismDegree) as executor:
        res = executor.map(get, urls)
    # Concatenate lists (lol python)
    return [o for o in res]

# Get ticket list by group id
def getTicketsByGroup(group, page):
    url = apiUrl + 'tickets/search?access_key=' \
        + goodKey + '&page=' + str(page) + '&per_page=100&query=company.id:' \
        + group
    return url

# Get ticket list by queue id
def getTicketsByQueue(queue, page):
    url = apiUrl + 'tickets/search?access_key=' \
        + goodKey + '&page=' + str(page) + '&per_page=100&query=queue.id:' \
        + queue
    return url

def collectAllPages(func, id):
    def recursiveCollect(result, query, id, page):
        pageResult = query(id, page)
        if (len(pageResult)==0):
            return result
        else:
            return recursiveCollect(result + pageResult, query, id, page + 1)
    return recursiveCollect([], func, id, 1)

# Get ticket info per ticket id
def getTicketInfo(id):
    url = apiUrl + 'tickets/' + str(id) + '?access_key=' \
        + goodKey + '&page=1&per_page=1000'
    return url

# Get users
def getUsers():
    url = apiUrl + 'users' + '?access_key=' \
        + goodKey + '&page=1&per_page=5000'
    r = requests.get(url, headers=headers)
    return r.json()

# Return element from array, otherwise empty string
def elemOrEmpty(l, index):
    try:
        l[index]
        return l[index]
    except IndexError:
        return ''
    except KeyError:
        return ''

# Transpose arbitrary list
def transposeList(list, size):
    return { ('comment_' + str(i).zfill(2)) : elemOrEmpty(list, i)
             for i in range(0, size) }

# Reformat datetime so that Jira understands
def reformatDate(s):
    d = datetime.datetime.strptime(s,'%Y-%m-%dT%H:%M:%S.%fZ')
    return d.strftime('%d/%m/%y %I:%M:%S %p')

# Transpose comments from list to columns
def transposeComments(comments, size):
    # Take body from every comment and transpose it to columns
    comments_sorted = sorted(comments, key = lambda k: k['created_on'])
    return transposeList(list(
        map(lambda c: 'Comment: ' + \
            c['related_data']['user']['full_name'] + ': ' + \
            reformatDate(c['created_on']) + ': ' + \
            c['body'], comments)), size)

# Additional processing of tickets after collecting detailed data
def ticketPostprocessing(ticketData):
    # Init result
    ticketsProcessed = []

    # Extract comment dict
    ticketComments = list(map(lambda i: i['all_comments'], ticketData))

    # We need equal amount of columns for all tickets, so we'll use max
    maxCommentsPerTicket = max(list(map(lambda l: len(l), ticketComments)))

    # Now let's transpose the comment section for every ticket. Amount
    # of columns is same for all tickets
    ticketCommentsTransposed = [
        transposeComments(i, maxCommentsPerTicket)
        for i in ticketComments ]
    
    # Extract relevant keys from dataset and transpose comments into columns
    for ticket in ticketData:
        ticketProcessed = {}

        # It's nice to have Id as first field
        ticketProcessed.update({'id': ticket['id']})

        # Copy fields from "related_data" section
        ticketProcessed.update({'user_email': ticket['related_data']['user']['email']})
        ticketProcessed.update({'assigned_to_email': ticket['related_data']['assignee_user']['email']})
        ticketProcessed.update({'ticket_type': ticket['related_data']['ticket_type_name']})
        ticketProcessed.update({'company_name': ticket['related_data']['company']['name']})

        # Copy fields from custom dictionaries
        ticketProcessed.update({'priority_txt': priorityDict[ticket['priority_id']]})
        ticketProcessed.update({'status_txt': statusDict[ticket['status_id']]})
        
        for ticketProp in ticket:
            if ticketProp == 'all_comments':
                ticketCommentsTransposed = transposeComments(
                    ticket['all_comments'], maxCommentsPerTicket)
                for comment in ticketCommentsTransposed:
                    ticketProcessed.update({comment: ticketCommentsTransposed[comment]})
            elif ticketProp in fieldsWeNeed:
                ticketProcessed.update({ticketProp:ticket[ticketProp]})
        
        ticketsProcessed.append(ticketProcessed)
    return ticketsProcessed

def getTicketIds():
    # Let's check if we already have something
    try:
        with open('ticketQueue.json', 'r') as f:
            content = f.read()
            ticketIds = eval(content)
    # If file does not exist
    except:
        print('Requesting ticket IDs')
        urls = [getTicketsByQueue(str(mojoQueueId),page) for page in range(100)]
        ticketsBatches = parallelGet(urls)
        tickets = [tId for ticketList in ticketsBatches for tId in ticketList]

        # Filter tickets by id
        ticketIds = dict(map(lambda i: (i['id'], False), tickets))

        with open('ticketQueue.json', 'w') as f:
            f.write(str(ticketIds))
            f.close()

    return ticketIds
    
# Main function
def main():
    
    # IO! Get the list of tickets which are not exported yet
    ticketIds = getTicketIds()

    # Initial calculation of tickets to export
    theWayToFindTicketsLeft = lambda t: [ key for (key, value) in t.items() if value == False ]
    ticketIdsLeft = theWayToFindTicketsLeft(ticketIds)

    # Packet size is a bit arbitrary
    packetSize = parallelismDegree * 2
    packetCount = len(ticketIdsLeft) // packetSize

    if len(ticketIdsLeft) == 0: 
        print('All tickets are loaded')       
    else:
        print('Downloading ticket data. ' + str(len(ticketIdsLeft)) + ' tickets left.')

        # Let's start the export loop
        for i in range(packetCount+1):
            print(str(i + 1) + ' of ' + str(packetCount+1))
            
            packetOfTicketIds =  ticketIdsLeft[:packetSize]
        
            # IO! Get full ticket data for each id
            urls = [getTicketInfo(ticketId) for ticketId in packetOfTicketIds]
            ticketData = parallelGet(urls)

            # Extract relevant keys from dataset and transpose
            # comments into columns
            ticketsProcessed = ticketPostprocessing(ticketData)
            
            # Write results as CSV
            keys = ticketsProcessed[0].keys()
            with open('ticketData.csv', 'a+') as writeFile:
                writer = csv.DictWriter(writeFile, keys, delimiter=';')
                #writer.writeheader()
                writer.writerows(ticketsProcessed)
                writeFile.close()

            # Update tickets that are downloaded
            for t in packetOfTicketIds:
                ticketIds.update({ t: True })

            # Save updated export state to file
            with open('ticketQueue.json', 'w') as f:
                f.write(str(ticketIds))
                f.close()

            # Update the ticket queue
            ticketIdsLeft = theWayToFindTicketsLeft(ticketIds)

        # Done
        print('Export job is finished')

def printHelp():
    print(\
          'Following options are mandatory:\n\
    -k {YOUR API KEY}\n\
    -q {MOJO QUEUE ID}\n\
          ')

sysInput = sys.argv
argumentList = sysInput[1:]

# Get access key
try:
    goodKey = argumentList[argumentList.index('-k')+1]
except:
    printHelp()
    sys.exit()

# Get queue id
try:
    mojoQueueId = argumentList[argumentList.index('-q')+1]
except:
    printHelp()
    sys.exit()
    
# Global variables
dn = 'https://app.mojohelpdesk.com'
apiUrl = dn + '/api/v2/'
headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}

# Perfomance tuning parameters
parallelismDegree = 12

fieldsWeNeed = [ 'updated_on'
                 ,'status_id'
                 ,'assigned_to_id'
                 ,'ticket_type_id'
                 ,'description'
                 ,'user_id'
                 ,'created_on'
                 ,'solved_on'
                 ,'priority_id'
                 ,'title'
                 ,'resolution_id']

priorityDict = {
    10 : 'emergency',
    20 : 'urgent',
    30 : 'normal',
    40 : 'low'
}

statusDict = {
    10 : 'new',
    20 : 'in progress',
    30 : 'on hold',
    40 : 'information requested',
    50 : 'solved',
    60 : 'closed'
}

# Restart our flow on errors
stillWorkToBeDone = True
while stillWorkToBeDone:
    try:
        main()
        stillWorkToBeDone = False
    except:
        print('Error occured, restarting')
        stillWorkToBeDone = True
