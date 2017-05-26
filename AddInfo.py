import urllib, urllib2, json, httplib
import arcpy
import codecs, os, sys
import shutil
import errno
import string
import datetime, time
import xml.dom.minidom as DOM
import socket
import tempfile
import getpass
import zipfile

longErrorGlobal = False   


def gentoken(server, port, adminUser, adminPass, expiration=300):
    
    #Re-usable function to get a token required for Admin changes
    query_dict = {'username':adminUser,'password':adminPass,'client':'requestip'}
    
    query_string = urllib.urlencode(query_dict)
    url = "http://{}:{}/arcgis/admin/generateToken".format(server, port)
    
    token = json.loads(urllib.urlopen(url + "?f=json", query_string).read())
        
    if 'token' not in token:
        arcpy.AddError(token['messages'])
        quit()
    else:
        return token['token']


def makeAGSconnection(server, port, adminUser, adminPass, workspace):
    
    ''' Function to create an ArcGIS Server connection file using the arcpy.Mapping function "CreateGISServerConnectionFile"    
    '''
    millis = int(round(time.time() * 1000))
    connectionType = 'ADMINISTER_GIS_SERVICES'
    connectionName = 'ServerConnection' + str(millis)
    serverURL = 'http://' + server + ':' + port + '/arcgis/admin'
    serverType = 'ARCGIS_SERVER'
    saveUserName = 'SAVE_USERNAME'
        
    outputAGS = os.path.join(workspace, connectionName + ".ags")
    try:
        arcpy.mapping.CreateGISServerConnectionFile(connectionType, workspace, connectionName, serverURL, serverType, True, '', adminUser, adminPass, saveUserName)
        return outputAGS
    except:
        arcpy.AddError("Could not create AGS connection file for: '" + server + ":" + port + "'")
        sys.exit()
        

# A function that will post HTTP POST request to the server
def postToServer(server, port, url, params):

    httpConn = httplib.HTTPConnection(server, port)
    headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain"}

    # URL encode the resoure URL
    url = urllib.quote(url.encode('utf-8'))
    
    # Build the connection to add the roles to the server
    httpConn.request("POST", url, params, headers)

    response = httpConn.getresponse()
    data = response.read()
    httpConn.close()
    
    return (response, data)


#Check if a service exists
def isServicePresent(server, port, adminUser, adminPass, serviceName, folderName, token=None):
    
    token = gentoken(server, port, adminUser, adminPass)
     
    # If the folder itself is not present, we do not need to check for the service's presence in this folder.
    if folderName != 'root' and folderName != '' and not isFolderPresent(folderName, server, port, token):
        return False

    params = urllib.urlencode({'token': token, 'f': 'json'})
        
    if  folderName == 'root' or folderName == '':
        URL = "/arcgis/admin/services/"       
    else:
        URL = "/arcgis/admin/services/" + folderName
    
    response, data = postToServer(server, port, URL, params)
        
    if (response.status != 200 or not assertJsonSuccess(data)):
        arcpy.AddMessage("\n     Error while fetching the service information from the server.")
        arcpy.AddMessage(str(data))
        return True
        
    #extract the services from the JSON response
    servicesJSON = json.loads(data)
    services = servicesJSON['services']
    
    for service in services:
        if service['serviceName'] == serviceName: return True

    return False


#Check if a folder is present
def isFolderPresent(folderName, server, port, token):
    
    params = urllib.urlencode({'token': token, 'f': 'json'})    
    folderURL = "/arcgis/admin/services"
    
    response, data = postToServer(server, port, folderURL, params)
        
    if (response.status != 200 or not assertJsonSuccess(data)):
        arcpy.AddMessage("\n     Error while fetching folders from the server.")
        arcpy.AddMessage(str(data))
        return True
    
    servicesJSON = json.loads(data)
    folders = servicesJSON['folders']
    
    for folder in folders:
        if folder == folderName: return True

    return False

def numberOfServices(server, port, adminUser, adminPass, serviceType):
    
    #Count all the services of "MapServer" type in a server
    number = 0
    token = gentoken(server, port, adminUser, adminPass)    
    services = []    
    baseUrl = "http://{}:{}/arcgis/admin/services".format(server, port)
    catalog = json.load(urllib2.urlopen(baseUrl + "/" + "?f=json&token=" + token))
    services = catalog['services']
    
    for service in services:
        if service['type'] == serviceType:
            number = number + 1
            
    folders = catalog['folders']
    
    for folderName in folders:
        catalog = json.load(urllib2.urlopen(baseUrl + "/" + folderName + "?f=json&token=" + token))
        services = catalog['services']
        for service in services:
            if service['type'] == serviceType:
                number = number + 1

    return number


# A function that checks that the input JSON object is not an error object.
def assertJsonSuccess(data):
    
    obj = json.loads(data)
    if 'status' in obj and obj['status'] == "error":
        arcpy.AddMessage("     Error: JSON object returns an error. " + str(obj))
        return False
    else:
        return True


def copy(src, dest):

    global longErrorGlobal
    
    #Check if folder exists, if exists delete
    if os.path.exists(dest): shutil.rmtree(dest)
    
    #Copy folder
    try:
        shutil.copytree(src, dest)
        return True
    except OSError as e:
        # If the error was caused because the source wasn't a directory
        if e.errno == errno.ENOTDIR:
            arcpy.AddMessage('src: ' +src)
            arcpy.AddMessage('dst: ' + dst)
            shutil.copy(src, dst)
            return True
        elif e.errno == errno.EEXIST:
            arcpy.AddMessage('     The folder already exists.')
            return False
        else:
            arcpy.AddMessage('     Directory not copied. Error: %s' % e)
            return True
    except:
        longErrorGlobal = True
        return False
    
def createZipFile(folder_path, output_path):
    """Zip the contents of an entire folder (with that folder included
    in the archive). Empty subfolders will be included in the archive
    as well.
    """

    parent_folder = os.path.dirname(folder_path)
    # Retrieve the paths of the folder contents.
    contents = os.walk(folder_path)
    try:
        zip_file = zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED)
        for root, folders, files in contents:
            # Include all subfolders, including empty ones.
            for folder_name in folders:
                absolute_path = os.path.join(root, folder_name)
                relative_path = absolute_path.replace(parent_folder + '\\','')
                zip_file.write(absolute_path, relative_path)
                
            for file_name in files:
                absolute_path = os.path.join(root, file_name)
                relative_path = absolute_path.replace(parent_folder + '\\','')
                zip_file.write(absolute_path, relative_path)

        zip_file.close()
        return True
    
    except IOError, message:
        zip_file.close()
        
        os.remove(output_path)
        return False
    except OSError, message:
        zip_file.close()
        
        os.remove(output_path)
        return False
    except zipfile.BadZipfile, message:
        zip_file.close()
        
        os.remove(output_path)
        return False
    
    except:
        zip_file.close()
        
        arcpy.AddMessage('     The source can not be copied because the path is extremely long.')
        os.remove(output_path)
        return False
    
def formatDate():
    return str(time.strftime('%Y-%m-%d %H:%M:%S'))
 
  
def addMetadata(fromServerName, fromServerPort, fromAdminUser, fromAdminPass, serviceList, serviceType, summaryParam, serviceDescriptionParam, tagsParam, authorParam, titleParam, creditsParam, mapNameParam, descriptionParam, summaryOverwrite, serviceDescriptionOverwrite, tagsOverwrite, authorOverwrite, titleOverwrite, creditsOverwrite, mapNameOverwrite, descriptionOverwrite, workspace, token=None):
    serviceSuccesNumber = 0
    serviceFailureNumber = 0
    sources = ""

    workspace = workspace + "\\"
    
    content1 = "\n *************************************************************************** \n           Publishing metadata ************************************************************ "
  
    # Getting services from tool validation creates a semicolon delimited list that needs to be broken up
    services = serviceList.split(';')
    
    con = makeAGSconnection(fromServerName, fromServerPort, fromAdminUser, fromAdminPass, workspace)

    #modify the services(s)    
    for service in services:
        service = urllib.quote(service.encode('utf8'))
        serviceURL = "/arcgis/admin/services/" + service        

        # Get and set the token
        token = gentoken(fromServerName, fromServerPort, fromAdminUser, fromAdminPass)

        # This request only needs the token and the response formatting parameter 
        params = urllib.urlencode({'token': token, 'f': 'json'})
        response, data = postToServer(fromServerName, str(fromServerPort), serviceURL, params)
        
        if (response.status != 200):
            arcpy.AddMessage("\n  ** Could not read service '" + str(service) + "' information.")
        else:
            # Check that data returned is not an error object
            if not assertJsonSuccess(data): arcpy.AddMessage("\n  ** Error when reading service '" + str(service) + "' information. " + str(data))
            else:
                arcpy.AddMessage("\n  ** Service '" + str(service) + "' information read successfully. Now transfering... (5 steps)")

                # Deserialize response into Python object
                propInitialService = json.loads(data)
                
                user = getpass.getuser()

                pathInitial = propInitialService["properties"]["filePath"]
                pathInitial = pathInitial.replace(':', '', 1)
                msdPath = pathInitial.replace('X', os.path.join(r'\\' + fromServerName, 'x'), 1)
                
                folderName = os.path.split(service)[0]

                serviceName = os.path.split(service)[1]
                serviceName2 = serviceName
                pos3 = serviceName2.find(".MapServer")
                simpleServiceName = serviceName2[:pos3]

                if  folderName != 'root' or folderName != '':                           
                    finalServiceName = folderName + "//" + simpleServiceName + ".MapServer"
                    temp_workspace = string.replace(workspace, ':', '', 1)
                    temp_workspace = string.replace(temp_workspace, 'X', os.path.join(r'\\' + socket.gethostname(), 'x'), 1)
                    sources = os.path.join(temp_workspace, os.path.join(folderName, simpleServiceName + ".MapServer"))

                else:
                    finalServiceName = serviceName
                    temp_workspace = string.replace(workspace, ':', '', 1)
                    sources = os.path.join(string.replace(temp_workspace, 'X', os.path.join(r'\\' + socket.gethostname(), 'x'), 1), serviceName)

                pos = msdPath.find(serviceName) + len(serviceName) 
                inputFolderPath = msdPath[:pos]

                arcpy.AddMessage("     Step 1: Copying original data")
                
                #Copy service data original data
                continuePublish1 = copy(inputFolderPath, workspace + "original\\" + serviceName)
                continuePublish2 = createZipFile(inputFolderPath, workspace + "original\\" + serviceName + ".zip")

                #Copy service data to modify
                workspace = workspace + "modified\\";
                continuePublish = copy(inputFolderPath, workspace + serviceName)

                #If the data copied ok
                if continuePublish == True and continuePublish1 == True and continuePublish2 == True:
                        mxdExist = False
                        #Check for MXD
                        for root, dirs, files in os.walk(workspace + serviceName):
                                for file in files:
                                        if file.endswith(".mxd"):
                                                 mxdFile = os.path.join(root, file)
                                                 mxdExist = True
                                                 break;
                                                                
                        #If MXD exist
                        if mxdExist == True:                                                                               

                                mapName = os.path.split(mxdFile)[1]
                                pos2 = mapName.find(".mxd")
                                sdname = mapName[:pos2]

                                sddraft = workspace + serviceName + "\\" + sdname + '.sddraft'
                                sd = workspace + serviceName + "\\" + sdname + '.sd'

                                mapDoc = arcpy.mapping.MapDocument(mxdFile)
                                dataframes = arcpy.mapping.ListDataFrames(mapDoc)

                                arcpy.AddMessage("     Step 2: Modifying services information")

                                if len(dataframes) > 1:
    
                                    restURL = "/arcgis/rest/services/" + folderName + "/" + simpleServiceName + "/MapServer"
                                    responseRest, dataRest = postToServer(fromServerName, str(fromServerPort), restURL, urllib.urlencode({'f': 'json'}))

                                    if (responseRest.status != 200):
                                        arcpy.AddMessage("\n  ** Could not read service '" + str(service) + "' information.")
                                    else:
                                        initialMapName = json.loads(dataRest)["mapName"]                                    
                                        for df in dataframes:
                                            if (df.name == initialMapName):
                                                if mapNameParam:
                                                    if mapNameOverwrite.upper() == 'TRUE':
                                                        df.name = mapNameParam
                                                        df.description = descriptionParam
                                                    else:
                                                        df.name = df.name + " " + mapNameParam
                                                if descriptionParam:
                                                    if descriptionOverwrite.upper() == 'TRUE':                                                    
                                                        df.description = descriptionParam
                                                    else:
                                                        df.description = df.description + " " + descriptionParam
                                                    
                                                break
                                else:
                                    if mapNameParam:
                                        if mapNameOverwrite.upper() == 'TRUE':                                        
                                            df = dataframes[0]
                                            df.name = mapNameParam
                                            df.description = descriptionParam
                                        else:
                                            df = dataframes[0]
                                            df.name = df.name + " " + mapNameParam                                    
                                            df.description = descriptionParam
                                        
                                if summaryParam:
                                    if summaryOverwrite.upper() == 'TRUE':
                                        mapDoc.summary = summaryParam
                                    else:
                                        mapDoc.summary = mapDoc.summary + " " + summaryParam

                                if serviceDescriptionParam:
                                    if serviceDescriptionOverwrite.upper() == 'TRUE':                                     
                                        mapDoc.description = serviceDescriptionParam
                                    else: 
                                        mapDoc.description = mapDoc.description + " " + serviceDescriptionParam                                        

                                if tagsParam:
                                    if tagsOverwrite.upper() == 'TRUE':                                    
                                        mapDoc.tags = tagsParam
                                    else:
                                        mapDoc.tags = mapDoc.tags + "," + tagsParam

                                if authorParam:
                                    if authorOverwrite.upper() == 'TRUE':                                    
                                        mapDoc.author = authorParam
                                    else:
                                        mapDoc.author = mapDoc.author + " " + authorParam
                                        
                                if creditsParam:
                                    if creditsOverwrite.upper() == 'TRUE':                                     
                                        mapDoc.credits = creditsParam
                                    else: 
                                        mapDoc.credits = mapDoc.credits + " " + creditsParam

                                if titleParam:
                                    if titleOverwrite.upper() == 'TRUE':                                    
                                        mapDoc.title = titleParam   
                                    else:                                     
                                        mapDoc.title = mapDoc.title + " " + titleParam                                    
                                    
                                mapDoc.save() 

                                #Create a customized Service Definition Draft
                                arcpy.AddMessage("     Step 3: Creating Service Definition Draft (.sddraft)")
                                draftXml = CreateServiceDefinitionDraft(mapDoc, sddraft, simpleServiceName, con, folderName, propInitialService, workspace + serviceName)

                                #Get the analysis result
                                arcpy.AddMessage("     Step 4: Analyzing Service Definition Draft.")

                                # Analyze the service definition draft
                                analyseDraft = analyseServiceDraft(draftXml, service)

                                # Stage and upload the service if the sddraft analysis did not contain errors
                                if analyseDraft['errors'] == {}:                                
                                        try:                                
                                                #If SD exist is deleted
                                                if os.path.isfile(sd): os.remove(sd)

                                                # Execute StageService. This creates the service definition.
                                                arcpy.AddMessage("     Step 5: Creating Service Definition (.sd)")
                                                arcpy.StageService_server(draftXml, sd)

                                                try:
                                                        # Set local variables
                                                        arcpy.AddMessage("     Step 6: Uploading Service Definition.")
                                                        arcpy.UploadServiceDefinition_server(sd, con)

                                                        serviceSuccesNumber = serviceSuccesNumber + 1

                                                except arcpy.ExecuteError:
                                                        arcpy.AddWarning("%%%%%%%%%%%%%%%%%%     " + arcpy.GetMessages())
                                                        arcpy.AddWarning("     Failed to publish.")

                                                        content = "\n " + formatDate() + "\n Failed to publish. \n   - " + finalServiceName + "\n"
                                                        serviceFailureNumber = serviceFailureNumber + 1

                                                #Published successfully.
                                                arcpy.AddMessage("  ** Service '" + finalServiceName + "' published successfully.")

                                        # SD can't be created
                                        except arcpy.ExecuteError:
                                                serviceTypeD = ""
                                                serverD = ""
                                                serviceD = ""
                                                databaseD = ""
                                                strconex = ""
                                                
                                                for lyr in arcpy.mapping.ListLayers(mapDoc):
                                                        if lyr.supports("SERVICEPROPERTIES"):
                                                                #Para no repetir las fuentes
                                                                if serviceTypeD != lyr.serviceProperties["ServiceType"] and serverD != lyr.serviceProperties["Server"] and serviceD != lyr.serviceProperties["Server"] and databaseD != lyr.serviceProperties["Database"]:
                                                                        serviceTypeD = lyr.serviceProperties["ServiceType"]
                                                                        serverD = lyr.serviceProperties["Server"]
                                                                        serviceD = lyr.serviceProperties["Service"]
                                                                        databaseD = lyr.serviceProperties["Database"]
                                                                        strconex = "          * ServiceType: '" + serviceTypeD + "', Server: '" + serverD + "', Service: '" + serviceD + "', Database: '" + databaseD + "'."
                                                del mapDoc
                                                del serviceTypeD
                                                del serverD
                                                del serviceD
                                                del databaseD
                                                
                                                if strconex != "":
                                                        arcpy.AddWarning("     Consolidating the data failed. Please register first the database in the Server DataStore: ")
                                                        arcpy.AddWarning(strconex)

                                                else:
                                                        arcpy.AddWarning("     Consolidating the data failed. Please check datasources.")
                                                serviceFailureNumber = serviceFailureNumber + 1

                                # if the sddraft analysis contained errors
                                else:
                                        #Service Definition Draft could not be analyzed
                                        if analyseDraft['errors'] == "NO":
                                                
                                                arcpy.AddWarning("     Service Definition Draft could not be analyzed.")
                                                
                                                content = "\n " + formatDate() + "\n Service Definition Draft could not be analyzed. \n   - " + finalServiceName + "\n"
                                                serviceFailureNumber = serviceFailureNumber + 1
                                        else:
                                                arcpy.AddWarning("     Service could not be published because errors were found during analysis. ")                             

                                                content = "\n " + formatDate() + "\n Service could not be published because errors were found during analysis. \n " + str(analyseDraft['errors']) + "\n   - " + finalServiceName + "\n"
                                                serviceFailureNumber = serviceFailureNumber + 1
                        # MXD not found
                        else:                              
                                arcpy.AddWarning("     Service MXD not found.")
                                
                                content = "\n " + formatDate() + "\n Service MXD not found.\n   - " + finalServiceName + "\n"
                                serviceFailureNumber = serviceFailureNumber + 1

                # Service information folder already exists (can't be deleted)
                else:
                        if longErrorGlobal == False:                        
                                arcpy.AddWarning("     Service information folder already exists and can not be created.")

                                content = "\n " + formatDate() + "\n Service information folder already exists and can not be created.\n   - " + finalServiceName + "\n"
                                serviceFailureNumber = serviceFailureNumber + 1
                        else:
                                arcpy.AddWarning("     The source can not be copied because the path is extremely long.")

                                content = "\n " + formatDate() + "\n The source can not be copied because the path is extremely long.\n   - " + finalServiceName + "\n"
                                serviceFailureNumber = serviceFailureNumber + 1                

    number = numberOfServices(fromServerName, fromServerPort, fromAdminUser, fromAdminPass, serviceType)

    temp_workspace = string.replace(workspace,':','',1)
    migration_backup = string.replace(temp_workspace, 'X', os.path.join(r'\\' + socket.gethostname(), 'x'), 1)
    
    arcpy.AddMessage("\n***************************************************************************  ")
    arcpy.AddMessage(" - Number of services in '" + fromServerName + "': " + str(number))
    arcpy.AddMessage(" - Number of services selected in '" + fromServerName + "': " + str(len(services)))
    arcpy.AddMessage(" - Number of services successfully edited: " + str(serviceSuccesNumber))
    arcpy.AddMessage(" - Number of services not edited: " + str(serviceFailureNumber))
        
    arcpy.AddMessage("***************************************************************************  ")

     
def CreateServiceDefinitionDraft(mapDoc, sddraft, service, con, folder, dataObj, iteminfoworkspace):
    #arcpy.mapping.CreateMapSDDraft(mapDoc, sddraft, service, 'ARCGIS_SERVER', con, True, folder)
    #return sddraft

    iteminfoExist = False
    #Check for item description
    for root, dirs, files in os.walk(iteminfoworkspace):
        for file in files:
            if file == "iteminfo.xml":
                iteminfoFile = os.path.join(root, file)
                iteminfoExist = True
                break;

    if iteminfoExist == True:
        # Read the sddraft xml.
        docItemInfo = DOM.parse(iteminfoFile)
##        try:
##            tags = docItemInfo.getElementsByTagName('tags')[0].firstChild.data
##        except:
##            tags = ""
##        try:
##            summary = docItemInfo.getElementsByTagName('summary')[0].firstChild.data
##        except:
##            summary = ""            

        # Create service definition draft
        arcpy.mapping.CreateMapSDDraft(mapDoc, sddraft, service, 'ARCGIS_SERVER', con, True, folder)
    else:
        # Create service definition draft
        arcpy.mapping.CreateMapSDDraft(mapDoc, sddraft, service, 'ARCGIS_SERVER', con, True, folder)


    # Read the sddraft xml.
    doc = DOM.parse(sddraft)
                    
    # Find all elements named TypeName. This is where the server object extension (SOE) names are defined.
    extensionsMSD = dataObj["extensions"]
    typeNames = doc.getElementsByTagName('TypeName')
    
    # Get the TypeName whose properties we want to modify.
    for typeName in typeNames:
        found = False
        active = "false"
        
        #Search fot the extension in the original MSD
        for extensionMSD in extensionsMSD:
            if typeName.firstChild.data == extensionMSD["typeName"]:
                found = True
                active = extensionMSD["enabled"]
                capabilities = extensionMSD["capabilities"]
                properties = extensionMSD["properties"]

                #If is there
                if found:
                    extension = typeName.parentNode
                    for extElement in extension.childNodes:
                        if extElement.tagName == 'Enabled':
                            extElement.firstChild.data = active
                            
                        elif extElement.tagName == 'Props':                    
                            for propNodes in extElement.childNodes:
                                for propNode in propNodes.childNodes:                        
                                    if propNode.childNodes[0].tagName == 'Key':
                                        try:                                            
                                            propNode.childNodes[1].firstChild.data = extensionMSD["properties"][propNode.childNodes[0].firstChild.data]
                                        except Exception, e:                                
                                            try:
                                                textnode = docItemInfo.createTextNode(extensionMSD["properties"][propNode.childNodes[0].firstChild.data])
                                                propNode.childNodes[1].appendChild(textnode)
                                            except Exception, e:
                                                print ''
                                            
                        elif extElement.tagName == 'Info':
                            for infoNodes in extElement.childNodes:
                                for infoNode in infoNodes.childNodes:                
                                    try:
                                        if infoNode.childNodes[0].tagName == 'Key' and infoNode.childNodes[0].firstChild.data == 'WebCapabilities':
                                            infoNode.childNodes[1].firstChild.data = capabilities
                                        #elif infoNode.childNodes[0].tagName == 'Key' and infoNode.childNodes[0].firstChild.data == 'WebEnabled':
                                        #    arcpy.AddMessage('WebEnabled ' + infoNode.childNodes[1].lastChild.data)                                    
                                            
                                    except Exception, e:
                                        print ''                       


    # turn on caching in the configuration properties
    propertiesMSD = dataObj["properties"]
    
    configProperties = doc.getElementsByTagName('ConfigurationProperties')[0]
    configPropertiesArray = configProperties.firstChild
    configPropertiesSet = configPropertiesArray.childNodes
    for configPropertySet in configPropertiesSet:
        keyValues = configPropertySet.childNodes
        for keyValue in keyValues:
            if keyValue.tagName == 'Key':
                if keyValue.firstChild.data == "supportedImageReturnTypes":
                    try:
                        keyValue.nextSibling.firstChild.data = propertiesMSD["supportedImageReturnTypes"]
                    except Exception, e:
                        print keyValue, keyValue.firstChild
                elif keyValue.firstChild.data == "useLocalCacheDir":
                    try:
                        keyValue.nextSibling.firstChild.data = propertiesMSD["useLocalCacheDir"]
                    except Exception, e:
                        print keyValue                   
                elif keyValue.firstChild.data == "isCached":
                    try:
                        keyValue.nextSibling.firstChild.data = propertiesMSD["isCached"]
                    except Exception, e:
                        print keyValue                    
                elif keyValue.firstChild.data == "clientCachingAllowed": 
                    try:                   
                        keyValue.nextSibling.firstChild.data = propertiesMSD["clientCachingAllowed"]
                    except Exception, e:
                        print keyValue                   
                elif keyValue.firstChild.data == "schemaLockingEnabled": 
                    try:                   
                        keyValue.nextSibling.firstChild.data = propertiesMSD["schemaLockingEnabled"]
                    except Exception, e:
                        print keyValue                   
                elif keyValue.firstChild.data == "textAntialiasingMode":  
                    try:                  
                        keyValue.nextSibling.firstChild.data = propertiesMSD["textAntialiasingMode"]
                    except Exception, e:
                        print keyValue                        
                elif keyValue.firstChild.data == "enableDynamicLayers":   
                    try:                 
                        keyValue.nextSibling.firstChild.data = propertiesMSD["enableDynamicLayers"]
                    except Exception, e:
                        print keyValue                   
                elif keyValue.firstChild.data == "antialiasingMode":  
                    try:                  
                        keyValue.nextSibling.firstChild.data = propertiesMSD["antialiasingMode"]
                    except Exception, e:
                        print keyValue                   
                elif keyValue.firstChild.data == "maxRecordCount":
                    try:
                        keyValue.nextSibling.firstChild.data = propertiesMSD["maxRecordCount"]
                    except Exception, e:
                        print keyValue                   
                elif keyValue.firstChild.data == "dynamicDataWorkspaces": 
                    try:                   
                        keyValue.nextSibling.firstChild.data = propertiesMSD["dynamicDataWorkspaces"]
                    except Exception, e:
                        print keyValue                   
                elif keyValue.firstChild.data == "MaxImageHeight":      
                    try:              
                        keyValue.nextSibling.firstChild.data = propertiesMSD["maxImageHeight"]
                    except Exception, e:
                        print keyValue                   
                elif keyValue.firstChild.data == "cacheOnDemand":  
                    try:                  
                        keyValue.nextSibling.firstChild.data = propertiesMSD["cacheOnDemand"]
                    except Exception, e:
                        print keyValue                   
                elif keyValue.firstChild.data == "maxBufferCount":   
                    try:                 
                        keyValue.nextSibling.firstChild.data = propertiesMSD["maxBufferCount"]
                    except Exception, e:
                        print keyValue                   
                elif keyValue.firstChild.data == "disableIdentifyRelates":  
                    try:                  
                        keyValue.nextSibling.firstChild.data = propertiesMSD["disableIdentifyRelates"]
                    except Exception, e:
                        print keyValue                    
                elif keyValue.firstChild.data == "MaxImageWidth":       
                    try:             
                        keyValue.nextSibling.firstChild.data = propertiesMSD["maxImageWidth"]
                    except Exception, e:
                        print keyValue                   
                elif keyValue.firstChild.data == "maxScale":         
                    try:
                        if propertiesMSD["maxScale"] != "":
                            keyValue.nextSibling.firstChild.data = propertiesMSD["maxScale"]
                    except Exception, e:
                        print keyValue                   
                elif keyValue.firstChild.data == "maxDomainCodeCount":   
                    try:                 
                        keyValue.nextSibling.firstChild.data = propertiesMSD["maxDomainCodeCount"]
                    except Exception, e:
                        print keyValue                   
                elif keyValue.firstChild.data == "minScale":   
                    try:
                        if propertiesMSD["minScale"] != "":
                            keyValue.nextSibling.firstChild.data = propertiesMSD["minScale"]
                    except Exception, e:
                        print keyValue                   
                elif keyValue.firstChild.data == "ignoreCache":   
                    try:                 
                        keyValue.nextSibling.firstChild.data = propertiesMSD["ignoreCache"]
                    except Exception, e:
                        print keyValue                   


    # turn on caching in the configuration properties
    props = doc.getElementsByTagName('Props')[0]
    propsArray = props.firstChild
    propSets = propsArray.childNodes
    for propSet in propSets:
        keyValues = propSet.childNodes
        for keyValue in keyValues:
            if keyValue.tagName == 'Key':
                if keyValue.firstChild.data == "MaxInstances":
                    try:
                        keyValue.nextSibling.firstChild.data = dataObj["maxInstancesPerNode"]
                    except Exception, e:
                        print keyValue
                elif keyValue.firstChild.data == "keepAliveInterval":
                    try:
                        keyValue.nextSibling.firstChild.data = dataObj["keepAliveInterval"]
                    except Exception, e:
                        print keyValue
                elif keyValue.firstChild.data == "StartupTimeout":
                    try:
                        keyValue.nextSibling.firstChild.data = dataObj["maxStartupTime"]
                    except Exception, e:
                        print keyValue
                elif keyValue.firstChild.data == "configuredState":
                    try:
                        keyValue.nextSibling.firstChild.data = dataObj["configuredState"]
                    except Exception, e:
                        print keyValue
                elif keyValue.firstChild.data == "UsageTimeout":
                    try:
                        keyValue.nextSibling.firstChild.data = dataObj["maxUsageTime"]
                    except Exception, e:
                        print keyValue
                elif keyValue.firstChild.data == "Isolation":
                    try:
                        keyValue.nextSibling.firstChild.data = dataObj["isolationLevel"]
                    except Exception, e:
                        print keyValue
                elif keyValue.firstChild.data == "IdleTimeout":
                    try:
                        keyValue.nextSibling.firstChild.data = dataObj["maxIdleTime"]
                    except Exception, e:
                        print keyValue
                elif keyValue.firstChild.data == "MinInstances":
                    try:
                        keyValue.nextSibling.firstChild.data = dataObj["minInstancesPerNode"]
                    except Exception, e:
                        print keyValue
                elif keyValue.firstChild.data == "WaitTimeout":
                    try:
                        keyValue.nextSibling.firstChild.data = dataObj["maxWaitTime"]
                    except Exception, e:
                        print keyValue
                elif keyValue.firstChild.data == "InstancesPerContainer":
                    try:
                        keyValue.nextSibling.firstChild.data = dataObj["instancesPerContainer"]
                    except Exception, e:
                        print keyValue
                elif keyValue.firstChild.data == "recycleInterval":
                    try:
                        keyValue.nextSibling.firstChild.data = dataObj["recycleInterval"]
                    except Exception, e:
                        print keyValue                  
                elif keyValue.firstChild.data == "recycleStartTime":
                    try:
                        keyValue.nextSibling.firstChild.data = dataObj["recycleStartTime"]
                    except Exception, e:
                        print keyValue

    if iteminfoExist == True:
        doc.getElementsByTagName('XMin')[0].firstChild.data = docItemInfo.getElementsByTagName('xmin')[0].firstChild.data
        doc.getElementsByTagName('YMin')[0].firstChild.data = docItemInfo.getElementsByTagName('ymin')[0].firstChild.data
        doc.getElementsByTagName('XMax')[0].firstChild.data = docItemInfo.getElementsByTagName('xmax')[0].firstChild.data
        doc.getElementsByTagName('YMax')[0].firstChild.data = docItemInfo.getElementsByTagName('ymax')[0].firstChild.data        
        
    # turn on caching in the configuration properties
    itemInfo = doc.getElementsByTagName('ItemInfo')[0]
    itemInfoSets = itemInfo.childNodes
    for itemInfoSet in itemInfoSets:         
        if itemInfoSet.tagName == "MinScale":
            try:
                if propertiesMSD["minScale"] != "":
                    itemInfoSet.firstChild.data = propertiesMSD["minScale"]
            except Exception, e:
                print itemInfoSet.tagName
        elif itemInfoSet.tagName == "MaxScale":
            try:
                if propertiesMSD["maxScale"] != "":
                    itemInfoSet.firstChild.data = propertiesMSD["maxScale"]            
            except Exception, e:
                print itemInfoSet.tagName

    # Output to a new sddraft.
    outXml = sddraft[:-8] + "_mod.sddraft"
    if os.path.exists(outXml): os.remove(outXml)
    f = codecs.open(outXml, "w", "utf-8")
    doc.writexml(f)
    f.close()

    os.remove(sddraft)
    
    return outXml


def analyseServiceDraft(draftXml, service):
    analysis = {}
    try:    
        # Analyze the service definition draft
        analysis = arcpy.mapping.AnalyzeForSD(draftXml)

        # Print errors, warnings, and messages returned from the analysis
        count = 0 
        mess = "     The following information was returned during analysis of the MXD: "
        for key in ('messages', 'warnings', 'errors'):
            mess = mess + "\n      " + key.upper() + ":"
            vars = analysis[key]
            mess2 = ""
            for ((message, code), layerlist) in vars.iteritems():
                mess2 = mess2 + "\n      - " + message + " (CODE %i)" % code
                mess2 = mess2 + " applies to:"
                
                for layer in layerlist:
                    count = count + 1
                    mess2 = mess2 + "\n            " + str(count) + " : "+ layer.name

            mess = mess + mess2
            if analysis['errors'] != {}:
                analysis['errors'] = mess
                arcpy.AddMessage(mess)
                
            return analysis
        
    # if the sddraft analysis fails
    except:
        #Service Definition Draft could not be analyzed
        analysis['errors'] = "NO"
        return analysis

   
if __name__ == "__main__":

    # Gather inputs    
    fromServerName = arcpy.GetParameterAsText(0)
    fromServerPort = arcpy.GetParameterAsText(1)
    fromAdminUser = arcpy.GetParameterAsText(2)
    fromAdminPass = arcpy.GetParameterAsText(3)
    serviceType = arcpy.GetParameterAsText(4) 
    serviceList = arcpy.GetParameterAsText(5)

    summaryParam = arcpy.GetParameterAsText(6)
    summaryOverwrite = arcpy.GetParameterAsText(7)
    serviceDescriptionParam = arcpy.GetParameterAsText(8)
    serviceDescriptionOverwrite = arcpy.GetParameterAsText(8)    
    tagsParam = arcpy.GetParameterAsText(10)
    tagsOverwrite = arcpy.GetParameterAsText(11)
    authorParam = arcpy.GetParameterAsText(12)
    authorOverwrite = arcpy.GetParameterAsText(13)
    titleParam = arcpy.GetParameterAsText(14)
    titleOverwrite = arcpy.GetParameterAsText(15)
    creditsParam = arcpy.GetParameterAsText(16)
    creditsOverwrite = arcpy.GetParameterAsText(17)
    mapNameParam = arcpy.GetParameterAsText(18)
    mapNameOverwrite = arcpy.GetParameterAsText(19)
    descriptionParam = arcpy.GetParameterAsText(20)
    descriptionOverwrite = arcpy.GetParameterAsText(21)
    
    metadataFolder = arcpy.GetParameterAsText(22)

    
    if not os.path.exists(metadataFolder):
        os.makedirs(metadataFolder)
        
    now = datetime.datetime.now()
    workspace = os.path.join(metadataFolder, str(now.year) + str(now.month) + str(now.day) + '_' + str(now.hour) + str(now.minute) + str(now.second) + '_' + fromServerName)
    
    if not os.path.exists(workspace): os.makedirs(workspace)

    if serviceType == "MapServer":
        addMetadata(fromServerName, fromServerPort, fromAdminUser, fromAdminPass, serviceList, serviceType, summaryParam, serviceDescriptionParam, tagsParam, authorParam, titleParam, creditsParam, mapNameParam, descriptionParam, summaryOverwrite, serviceDescriptionOverwrite, tagsOverwrite, authorOverwrite, titleOverwrite, creditsOverwrite, mapNameOverwrite, descriptionOverwrite, workspace)
