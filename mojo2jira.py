import requests
import sys
import json
import csv
import datetime

# Get ticket list by group id
def getTicketsByGroup(group, page):
    url = apiUrl + 'tickets/search?access_key=' \
        + goodKey + '&page=' + str(page) + '&per_page=100&query=company.id:' \
        + group
    attempt = 0
    while attempt < 3:
        try:
            r = requests.get(url, headers=headers)
        except requests.exceptions.RequestException:
            attempt + 1
    return r.json()

# Get ticket list by queue id
def getTicketsByQueue(queue, page):
    url = apiUrl + 'tickets/search?access_key=' \
        + goodKey + '&page=' + str(page) + '&per_page=100&query=queue.id:' \
        + queue
    attempt = 0
    while attempt < 3:
        try:
            r = requests.get(url, headers=headers)
        except requests.exceptions.RequestException:
            attempt + 1
    return r.json()

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
    url = apiUrl + 'tickets/' + id + '?access_key=' \
        + goodKey + '&page=1&per_page=1000'
    r = requests.get(url, headers=headers)
    return r.json()

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

# Print a "." w/o a carriage return
def showProgress():
    sys.stdout.write(".") # write w/o \n
    sys.stdout.flush()

# Main function
def main():

    # IO! Search for tickets from specified group
    print('Get ticket list')
    showProgress()
    tickets = collectAllPages(getTicketsByQueue,'76784')

    # Filter tickets by id
    ticketIds = list(map(lambda i: i['id'], tickets))

    # IO! Get full ticket data for each id
    print('Get ticket data')
    showProgress()
    ticketData = list(map(lambda i: getTicketInfo(str(i)), ticketIds))

    # Comment dict
    print('Postprocess data')
    showProgress()
    ticketComments = list(map(lambda i: i['all_comments'], ticketData))

    # We need equal amount of columns for all tickets, so we'll use max
    maxCommentsPerTicket = max(list(map(lambda l: len(l), ticketComments)))

    # Now let's transpose the comment section for every ticket. Amount
    # of columns is same for all tickets
    ticketCommentsTransposed = [
        transposeComments(i, maxCommentsPerTicket)
        for i in ticketComments ]
    
    # Extract relevant keys from dataset and transpose comments into columns
    ticketsProcessed = []
    for ticket in ticketData:
        ticketProcessed = {}
        for ticketProp in ticket:
            if ticketProp == 'all_comments':
                ticketCommentsTransposed = transposeComments(
                    ticket['all_comments'], maxCommentsPerTicket)
                for comment in ticketCommentsTransposed:
                    ticketProcessed.update({comment: ticketCommentsTransposed[comment]})
            elif ticketProp in fieldsWeNeed:
                ticketProcessed.update({ticketProp:ticket[ticketProp]})

        # Copy fields from "related_data" section
        ticketProcessed.update({'user_email': ticket['related_data']['user']['email']})
        ticketProcessed.update({'assigned_to_email': ticket['related_data']['assignee_user']['email']})
        ticketProcessed.update({'ticket_type': ticket['related_data']['ticket_type_name']})
        ticketProcessed.update({'company_name': ticket['related_data']['company']['name']})

        # Copy fields from custom dictionaries
        ticketProcessed.update({'priority_txt': priorityDict[ticketProcessed['priority_id']]})
        ticketProcessed.update({'status_txt': statusDict[ticketProcessed['status_id']]})
        
        ticketsProcessed.append(ticketProcessed)

    print('Write data to disc')
    showProgress()
    # Write results as JSON
    f = open('ticketData.json', 'w')
    f.write(json.dumps(ticketsProcessed))

    # Write results as CSV
    keys = ticketsProcessed[0].keys()
    with open('ticketData.csv', 'w') as writeFile:
        writer = csv.DictWriter(writeFile, keys, delimiter=';')
        writer.writeheader()
        writer.writerows(ticketsProcessed)
    writeFile.close()
    
# Global variables
dn = 'https://app.mojohelpdesk.com'
goodKey = 'a2094c56add92ae504d42bb2e7c01e4625971e09' # Get access key
apiUrl = dn + '/api/v2/'
headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}

fieldsWeNeed = [ 'id'
                 ,'updated_on'
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

# start execution
main()
