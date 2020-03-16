import zmq
import socket
from collections import defaultdict

def getIp():
    s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    s.connect(("8.8.8.8",80))
    return s.getsockname()[0]


def clientRequestHandler(message, masterDataFile, dataKeepersState, syncLock):
    if message[0] == "upload":
        # Checks whether there is a free port (j) for each ip (i)
        for i in dataKeepersState:
            for j in dataKeepersState[i]:
                syncLock.acquire()
                if(dataKeepersState[i][j]):
                    dataKeepersState[i][j] = False # Make Port Busy
                    syncLock.release()
                    return [i,j,message[1]]
                syncLock.release()
    elif message[0] == "download":
        for i in masterDataFile:
            for j in masterDataFile[i]:
                for k in masterDataFile[i][j]:
                    syncLock.acquire()
                    if k == message[1] and dataKeepersState[i][j]:
                        dataKeepersState[i][j] = False # Make Port Busy
                        syncLock.release()
                        return [i,j,message[1]]
                    syncLock.release()
    return None


def masterClientConnection(clientSocket,masterDataFile, dataKeepersState,syncLock):
    # Sending/Receiving data from client
    # Wait for next request from client
    message = []
    try:
        message = clientSocket.recv_pyobj()
        print(message)
    except zmq.error.Again:
        return
    # TODO: Function made by friedPotato7 use messege[upload/download,filename.mp4] and return arr[ip,port#,path of file] replaced by 8000
    # port = ["tcp://localhost:",8000,"Alberto Mardegan - Selfie del futuro.mp4"]
    port = clientRequestHandler(message, masterDataFile, dataKeepersState,syncLock)
    clientSocket.send_pyobj(port)

def masterDatakeeperConnection(masterIndex,datakeeperSocket,filesDictionary, masterDataFile, dataKeepersState):
    
    try:
        string = datakeeperSocket.recv_string()
        topic, messagedata , NodeIndex , processesIndex  = string.split()
    except zmq.error.Again:
        return
    if topic=="1" and messagedata=="1" :
        print("Master index "+ str(masterIndex )+" Node " +NodeIndex+" Process "+ processesIndex +" is Alive\n")
    #Master - datakeeper success message
    if topic=="2" :
        ip=NodeIndex
        port=processesIndex
        print("On Master index "+ str(masterIndex )+" File with Name: " + messagedata +" Has Successfully uploaded on Machine with ip: "+ ip+"\n" )
        addFile(ip,port,messagedata,filesDictionary)
        dataKeepersState[ip][port] = True
        masterDataFile[ip][port].append(messagedata)
        


def addFile (ip,port,fileName,filesDictionary):
    if(len(filesDictionary[fileName]) == 0):
        temp = nested_dict(1,list)
        filesDictionary[fileName].append(temp)
        filesDictionary[fileName].append(1)
    filesDictionary[fileName][1] += 1 
    filesDictionary[fileName][0][ip].append(port)  


def initialzeClientMasterConnection(masterIndex,startingPortMasterClient):
    # Bind ports for clients
    clientPort=startingPortMasterClient+masterIndex
    context = zmq.Context()
    clientSocket = context.socket(zmq.REP)
    clientSocket.bind("tcp://127.0.0.1:%s" % clientPort)
    clientSocket.RCVTIMEO = 1
    return clientSocket


def initialzeDatakeeperMasterConnection(masterIndex,numberOfNodes_Datakeeper, numberOfProcessesPerDataKeeper, masterDataFile, dataKeepersState, syncLock):
    # Bind ports for datakeeper
    print("Master index = "+ str(masterIndex))

    context1 = zmq.Context()
    masterReceiver = context1.socket(zmq.PULL)
    masterReceiver.bind("tcp://127.0.0.1:%s" % str(17777 + masterIndex)) # getIp()
    initializedDataKeepers = 0
    datakeepersAdresses=[]
    while initializedDataKeepers < numberOfNodes_Datakeeper * numberOfProcessesPerDataKeeper:
        address = masterReceiver.recv_pyobj()
        syncLock.acquire()
        masterDataFile["tcp://"+address["ip"]+":"][str(8000+address["nodeIndex"])] = []
        dataKeepersState["tcp://"+address["ip"]+":"][str(8000+address["nodeIndex"])]= True
        syncLock.release()
        if address["head"]:
            datakeepersAdresses.append("tcp://"+str(address["ip"])+":"+str(5556+address["nodeIndex"]))
        initializedDataKeepers += 1
    context = zmq.Context()
    datakeeperSocket = context.socket(zmq.SUB)
    for j in datakeepersAdresses:

        datakeeperSocket.connect(j)
    topicfilter = "1"
    datakeeperSocket.setsockopt_string(zmq.SUBSCRIBE, topicfilter)
    datakeeperSocket.RCVTIMEO = 1
    return datakeeperSocket


def nReplicatesMasterDatakeeper (masterIndex):
    context = zmq.Context()
    socket = context.socket(zmq.PUB)
    port=10000+masterIndex
    socket.bind("tcp://*:%s" %port)
    return socket

def makeNReplicates(filesDictionary,masterDataFile,syncLock,dataKeepersState,nrSocket,n):

    for file in filesDictionary:
        instance_count = filesDictionary[file][1] #get el instance count bta3 file 
        if instance_count < n:
            for i in range(n-instance_count): 
                source_machine = getSourceMachine(file,filesDictionary,dataKeepersState,syncLock)
                machine_to_copy_1 = selectMachineToCopyTo(masterDataFile,syncLock,dataKeepersState,file)
                NotifyMachineDataTransfer(source_machine, machine_to_copy_1,nrSocket)
            print("----------------------------------------------------------------------------------")
            print("--                            N Replicates Done  !!!                            --")
            print("----------------------------------------------------------------------------------")
        

def getSourceMachine(file,filesDictionary,dataKeepersState,syncLock):
    getFreeMachine=False
    srcMachine=[]
    srcMachine.append(file)
    while getFreeMachine == False:
        for ip in filesDictionary[file][0]:
            for port in filesDictionary[file][0][ip]:
                syncLock.acquire()
                if dataKeepersState[ip][port]:
                    getFreeMachine=True
                    dataKeepersState[ip][port] = False
                    syncLock.release()
                    srcMachine.append(ip)
                    srcMachine.append(port)
                    print("Source Machine Found \n")
                    return srcMachine
                syncLock.release()


def selectMachineToCopyTo(masterDataFile,syncLock,dataKeepersState,fileName):
    notFound=True
    selectMachine=False
    while selectMachine==False:
        for i in masterDataFile:
                for j in masterDataFile[i]:
                    notFound=True
                    for k in masterDataFile[i][j]:
                        if k==fileName:
                            notFound=False
                            break
                    syncLock.acquire()
                    if notFound==True and dataKeepersState[i][j]:
                        dataKeepersState[i][j] = False # Make Port Busy
                        syncLock.release()
                        selectMachine=True
                        print("Machine to Copy Found \n")
                        return[i,j]
                    syncLock.release()


def NotifyMachineDataTransfer(source_machine, machine_to_copy,nrSocket):
    msgToSrcMachine=["tcp://"+str(machine_to_copy[0])+":"+machine_to_copy[1],"Alberto Mardegan - Selfie del futuro.mp4","source_machine"]
    topic = "1"
    nrSocket.send("%d %d" % (topic, msgToSrcMachine))
    

def nested_dict(n, type):
    if n == 1:
        return defaultdict(type)
    else:
        return defaultdict(lambda: nested_dict(n-1, type))


def masterTracker(masterIndex,numberOfNodes_Datakeeper, numberOfProcessesPerDataKeeper, startingPortMasterClient,masterDataFile,dataKeepersState,syncLock, filesDictionary,replicatesCount):
    
    masterDataFile = nested_dict(2, list)
    dataKeepersState = nested_dict(2, bool)
    filesDictionary = nested_dict(1,list)


    clientSocket = initialzeClientMasterConnection(masterIndex,startingPortMasterClient)
    datakeeperSocket = initialzeDatakeeperMasterConnection(masterIndex,numberOfNodes_Datakeeper, numberOfProcessesPerDataKeeper, masterDataFile, dataKeepersState, syncLock)
    #nReplicates Master Datakeeper Connection
    nrSocket = nReplicatesMasterDatakeeper(masterIndex)
    while True:
        #Connecting with client
        masterClientConnection(clientSocket,masterDataFile, dataKeepersState, syncLock)
        # Connecting with data keepers
        masterDatakeeperConnection(masterIndex,datakeeperSocket,filesDictionary, masterDataFile, dataKeepersState)
        makeNReplicates(filesDictionary,masterDataFile,syncLock,dataKeepersState,nrSocket,replicatesCount)        