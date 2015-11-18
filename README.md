# discomap.AddInfoToServices
Add Info to Services

Description
Allows modifying the information of a service's MXD, republishing it and keeping a copy of the original information. Same information will be set on all the services, if the information is empty, original will be maintained.

Environment requirements
The tool is developped to run under Arcgis 10.3.1 (Python2.7)
The ArcGIS services sources must be placed in a path according to the following structure: \\server_name\x\arcgisserver\...
The user that executes the tool or/and the user from ArcGIS Server that uses the geoprocessing service, should be able to access to each network path where the service’s sources are placed in order to copy them. 
The server where the geoprocessing service is displayed or the one where the tool is executed requires space to store a copy of all the sources of the migrated services.

Installation
ArcGIS Tool
ArcGis tool is placed in the toolbox called “AddInfo”.. There is located the “AddInfo” tool.
 

Functionality

The script uses 23 parameters:
 [1] Server Name (string)
The host name of the server. Typically a single name or fully qualified server, such as myServer.esri.com
 [2] Server Port (string)
The port number for the ArcGIS Server. Typically this is 6080. If you have a web adapter installed with your GIS Server and have the REST Admin enabled you can connect using the web servers port number.
[3] Server User (long)
Administrative username.
[4] Server Password (string) 
Administrative password.
[5] Service Type (string)
The type of the service to backup.
[6] Services (Multiple Value)
One or more services to perform an action on. The tool will autopopulate with a list of services when the first 5 parameters are entered. Service names must be provided in the <ServiceName>.<ServiceType> style.
[7] Summary (string)
Information to set on summary property
[8] Summary_overwrite (boolean)
Check to overwrite/uncheck to add more info to the existing 
[9] Service_description (string)
Information to set on service description property
[10] Service_description_overwrite (boolean)
Check to overwrite/uncheck to add more info to the existing 
[11] Tags (string)
Information to set on tags property
[12] Tags_overwrite (boolean)
Check to overwrite/uncheck to add more info to the existing 
[13] Author (string)
Information to set on author property
[14] Author_overwrite (boolean)
Check to overwrite/uncheck to add more info to the existing 
 [15] Title (string)
Information to set on title property
[16] Title_overwrite (boolean)
Check to overwrite/uncheck to add more info to the existing 
 [17] Credits (string)
Information to set on credits property
[18] Credits_overwrite (boolean)
Check to overwrite/uncheck to add more info to the existing 
 [19] Map_name (string)
Information to set on map name property
[20] Map_name_overwrite (boolean)
Check to overwrite/uncheck to add more info to the existing 
[21] Description (string)
Information to set on description property
[22] Description_overwrite (boolean)
Check to overwrite/uncheck to add more info to the existing 
[23] Add_Info_Folder (string)
Where the original and modified sources are stored

The script uses the username and the password to connect to the server with a generatetoken action. After accessing to the server, all services are listed. The user selects the services to add the information to. It is possible to overwrite the current information or to add some new information to the current one.

