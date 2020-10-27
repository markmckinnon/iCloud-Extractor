#
# copy data from a persokns iCloud account.
#
# Copyright 2020 Mark McKinnon.
# Contact: mark <dot> mckinnon <at> gmail <dot> com
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import os
import click
import datetime
from pyicloud.base import PyiCloudService
import sys
from Database import SQLiteDb
import json
from shutil import copyfileobj

photoColumnNames = " filename, size, id, masterRecord_json, assetRecord_json"
photoTableName = "photo_records"
photoTableColumns = " filename text, size text, id text, masterRecord_json text, assetRecord_json text"
photoSqlBindVals = "?, ?, ?, ?, ?"

deviceColumnNames = "deviceid, content_json, data_json"
deviceTableName = "devices"
deviceTableColumns = "deviceid text, content_json text, data_json text"
deviceSqlBindVals = "?, ?, ?"

accountColumnNames = "account_udid, account_json"
accountTableName = "account"
accountTableColumns = "account_udid text, account_json text"
accountSqlBindVals = "?, ?"

contactColumnNames = "contact_number, contact_json"
contactTableName = "contacts"
contactTableColumns = "contact_number int, contact_json text"
contactSqlBindVals = "?, ?"

eventColumnNames = "event_number, event_json"
eventTableName = "events"
eventTableColumns = "event_number int, event_json text"
eventSqlBindVals = "?, ?"

reminderColumnNames = "reminder_number, reminder_list, reminder_json"
reminderTableName = "reminders"
reminderTableColumns = "reminder_number int, reminder_list text, reminder_json text"
reminderSqlBindVals = "?, ?, ?"

driveColumnNames = "file_name, file_size, parent_path, file_json"
driveTableName = "drive"
driveTableColumns = "file_name text, file_size int, parent_path text, file_json text"
driveSqlBindVals = "?, ?, ?, ?"

appNames = "dateCreated, drivewsid, docwsid, zone, name, type, maxDepth, supportedExtensions, supportedTypes, icons"
appTableName = "installedApps"
appTableColumns = "dateCreated text, drivewsid text, docwsid text, zone text, name text, type text, maxDepth text, supportedExtensions text, supportedTypes text, icons text"

def parseApps(appLists, SQLitedb):
    for appList in appLists:
        #print (appList)
        columnKeys = appList.keys()
        columnValues = appList.values()
        columnNames = ", ".join(columnKeys)
        columnBindVariables = SQLitedb.create_question_bind_variables(len(columnKeys))
        newColVals = []
        for colVals in columnValues:
            if isinstance(colVals, str):
                newColVals.append(colVals)
            elif isinstance(colVals, dict):
                newColVals.append(json.dumps(colVals))
            elif isinstance(colVals, list):
                colV = []
                for colv in colVals:
                    if isinstance(colv, dict):
                        colV.append(json.dumps(colv))
                    else:
                        colV.append(colv)
                newColVals.append (", ".join(colV))
            else:
                newColVals = colVals
        columnVal = ", ".join(newColVals)
        SQLitedb.InsertBindValues(appTableName, columnNames, columnBindVariables, newColVals)

def parseDrive(dirName, dirPath, SQLitedb, nodata):
    dirList = dirName.dir()
    for dir in dirList:
        driveList = dirName[dir]
        if driveList.type == 'folder' or driveList.type == 'app_library':
            if nodata:
                try:
                    os.makedirs(os.path.join(dirPath, driveList.name))
                except FileExistsError:
                    pass
                except:
                    print ("Error creating directory => " + os.path.join(dirPath, driveList.name))
            parseDrive(dirName[driveList.name], os.path.join(dirPath, driveList.name), SQLitedb, nodata)
            return
        else:
            drive = []
            drive.append(driveList.name)
            drive.append(driveList.size)
            drive.append(os.path.join(dirPath, dir))
            drive.append(json.dumps(driveList.data))
            SQLitedb.InsertBindValues(driveTableName, driveColumnNames, driveSqlBindVals, drive)
            if nodata:
                with driveList.open(stream=True) as response:
                    with open(os.path.join(dirPath, driveList.name), 'wb') as fileOut:
                        copyfileobj(response.raw, fileOut)

def createTables(SQLitedb, SQLiteDbName):
    SQLitedb.RemoveDB_File(SQLiteDbName)
    SQLitedb.Open(SQLiteDbName)
    SQLitedb.CreateTable(photoTableName, photoTableColumns)
    SQLitedb.CreateTable(deviceTableName, deviceTableColumns)
    SQLitedb.CreateTable(accountTableName, accountTableColumns)
    SQLitedb.CreateTable(contactTableName, contactTableColumns)
    SQLitedb.CreateTable(eventTableName, eventTableColumns)
    SQLitedb.CreateTable(reminderTableName, reminderTableColumns)
    SQLitedb.CreateTable(driveTableName, driveTableColumns)
    SQLitedb.CreateTable(appTableName, appTableColumns) 

def parseDevices(SQLitedb, api):
    deviceList = api.devices._devices
    deviceKeys = deviceList.keys()
    for deviceKey in deviceKeys:
        try:
            device = []
            device.append(deviceKey)
            device.append(json.dumps(deviceList[deviceKey].content))
            device.append(json.dumps(deviceList[deviceKey].data))
            SQLitedb.InsertBindValues(deviceTableName, deviceColumnNames, deviceSqlBindVals, device)
        except:
            print(device)
            print (type(device[0]))
            print (type(device[1]))

def parseContacts(SQLitedb, api):
    contacts = api.contacts.all()
    contactNumber = 0
    for contact in contacts:
        try:
            contactList = []
            contactList.append(contactNumber)
            contactNumber + 1
            contactList.append(json.dumps(contact))
            SQLitedb.InsertBindValues(contactTableName, contactColumnNames, contactSqlBindVals, contactList)
        except:
            print("Contact ==> " + str(contact))

def parseEvents(SQLitedb, api):
    from_dt = datetime.date(2000, 1, 1)
    to_dt = datetime.date(2020, 12, 31)
    events = api.calendar.events(from_dt, to_dt)
    eventNumber = 0
    for event in events:
        try:
            eventList = []
            eventList.append(eventNumber)
            eventNumber = eventNumber + 1
            eventList.append(json.dumps(event))
            SQLitedb.InsertBindValues(eventTableName, eventColumnNames, eventSqlBindVals, eventList)
        except:
            print(eventList)

def parseReminders(SQLitedb, api):
    rem = api.reminders
    remindersList = api.reminders.lists
    reminderNumber = 0
    for reminders in remindersList:
        objType = type(remindersList[reminders])
        if type(remindersList[reminders]) == list:
            for remindList in remindersList[reminders]:
                try:
                    reminder = []
                    reminder.append(reminderNumber)
                    reminderNumber = reminderNumber + 1
                    reminder.append(reminders)
                    reminder.append(json.dumps(remindList))
                    SQLitedb.InsertBindValues(reminderTableName, reminderColumnNames, reminderSqlBindVals, reminder)
                except:
                    print("Reminder ==> " + str(reminder))
        else:
            try:
                reminder = []
                reminder.append(reminderNumber)
                reminderNumber = reminderNumber + 1
                reminder.append("")
                reminder.append(json.dumps(remindList))
                SQLitedb.InsertBindValues(reminderTableName, reminderColumnNames, reminderSqlBindVals, reminder)
            except:
                print("Reminders ==> " + str(reminder))


def parseAccounts(SQLitedb, api):
    accountList = api.account
    accountDevices = accountList.devices
    for devices in accountDevices:
        try:
            account = []
            account.append(devices.udid)
            account.append(json.dumps(devices))
            SQLitedb.InsertBindValues(accountTableName, accountColumnNames, accountSqlBindVals, account)
        except:
            print(account)


def main(args):
    driveDownloadDir = os.path.join(args.download, "Drive")
    photoDownloadDir = os.path.join(args.download, "Photos")

    SQLiteDbName = args.sqliteoutput
    itunesUserName = args.username
    itunesPassword = args.password

    SQLitedb = SQLiteDb()
    createTables(SQLitedb, SQLiteDbName)

    #print('Setup Time Zone')
    #datetime.strftime('%X %x %Z')
    #os.environ['TZ'] = 'America/New_York'



    print('Py iCloud Services')
    api = PyiCloudService(itunesUserName, itunesPassword)

    if api.requires_2sa:
        print ("Two-factor authentication required. Your trusted devices are:")

        devices = api.trusted_devices
        for i, device in enumerate(devices):
            print ("  %s: %s" % (i, device.get('deviceName', "SMS to %s" % device.get('phoneNumber'))))

        device = click.prompt('Which device would you like to use?', default=0)
        device = devices[device]
        if not api.send_verification_code(device):
            print ("Failed to send verification code")
            sys.exit(1)

        code = click.prompt('Please enter validation code')
        if not api.validate_verification_code(device, code):
            print ("Failed to verify verification code")
            sys.exit(1)



    print ("Adding Applications")
    appLists = api.drive.app_list()
    parseApps(appLists, SQLitedb)

    iPhoneList = api.iphone
    print ("Adding Devices")
    parseDevices(SQLitedb, api)

    print ("Adding Accounts")
    parseAccounts(SQLitedb, api)

    # Not working as of this time, check out later
    #fileList = api.files.dir()

    print ("Adding Contacts")
    parseContacts(SQLitedb, api)
    print ("Adding Events")
    parseEvents(SQLitedb, api)
    print ("Adding Reminders")
    parseReminders(SQLitedb, api)

    print ("Adding Drive")
    dirList = api.drive.dir()
    for dir in dirList:
        driveList = api.drive[dir]
        if driveList.type == 'folder' or driveList.type == 'app_library':
            if args.nodata:
                try:
                    os.makedirs(os.path.join(driveDownloadDir, driveList.name))
                except FileExistsError:
                    pass
            parseDrive(driveList, os.path.join(driveDownloadDir, driveList.name), SQLitedb, args.nodata)
        else:
            drive = []
            drive.append(driveList.name)
            drive.append(driveList.size)
            drive.append(driveDownloadDir)
            drive.append(json.dumps(driveList.data))
            SQLitedb.InsertBindValues(driveTableName, driveColumnNames, driveSqlBindVals, drive)
            if args.nodata:
                with driveList.open(stream=True) as response:
                    with open(os.path.join(driveDownloadDir, driveList.name), 'wb') as fileOut:
                        copyfileobj(response.raw, fileOut)

    # Not working as of this time, check out later
    #fileList = api.files

    print ("Adding Photos")

    if args.nodata:
        try:
            os.makedirs(photoDownloadDir)
        except FileExistsError:
            pass

    albumList = api.photos.albums
    albumKeys = albumList.keys()
    #print (photoKeys)

    for albumName in albumKeys:
        for photo in api.photos.albums[albumName]:
            photoList = []
            photoList.append(photo.filename)
            photoList.append(photo.size)
            photoList.append(photo.id)
            photoList.append(json.dumps(photo._master_record))
            photoList.append(json.dumps(photo._asset_record))
            SQLitedb.InsertBindValues(photoTableName, photoColumnNames, photoSqlBindVals, photoList)
            if args.nodata:
                download = photo.download()
                with open(os.path.join(photoDownloadDir, photo.filename), 'wb') as opened_file:
                    opened_file.write(download.raw.read())

    SQLitedb.Close()

    print ("Complete")

    return


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Download information from an iCloud User Account:')
    parser.add_argument('--download', metavar='path', required=True,
                        help='Download Directory for photos and Drive')
    parser.add_argument('--sqliteoutput', metavar='path', required=True,
                        help='sqlite output database')
    parser.add_argument('--username', metavar='user name', required=True,
                        help='itunes username')
    parser.add_argument('--password', metavar='password', required=True,
                        help='itunes user password')
    parser.add_argument('--nodata', action='store_false', required=False,
                        help='If no data is requested')
    args = parser.parse_args()

    main(args)