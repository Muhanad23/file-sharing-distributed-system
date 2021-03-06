import multiprocessing 
import Master    
import Client
import DataKeeper
    

if __name__ == '__main__':
    numberOfprocessesOfMaster=5 #number of processes  multi-process(MasterTracker)
    numberOfprocessesOfNodes=3 #number of processes  multi-process(data keeper)
    numberOfNodes=1 #number of nodes of data keeper
    startingPortMasterClient=7000 #first port between client/master
    startingPortDatakeeperClient=8000 #first port between client/datakeeper
    masterIp="tcp://127.0.0.1:" #master ip
    replicatesCount=3 # count of replicates
    processes=[]
    manager = multiprocessing.Manager()
    masterDataFile = manager.dict() # masterDataFile = { ip1: { port1: [ file1, file2, ... ], port2: [...], ... }, ip2: {...} }
    dataKeepersState = manager.dict() # dataKeepersState = { ip1: { port1: True, port2: False, ... }, ip2: { port1: True, ... }, ... }
    syncLock = multiprocessing.RLock()
    iAmAliveDict = manager.dict()
    filesDictionary = manager.dict() # filesDictionary = { filename1: [ { ip1: [port1, port2, ...], ip2: [...], ... } , instanceCount], filename2: [...] }
    # filesDictionary["filenameKey.mp4"][1] = instanceCount
    # filesDictionary["filenameKey.mp4"][0]["tcp:127.0.0.1"] = [8000, 8001, 8002]

    for k in range(numberOfprocessesOfMaster):
        t= multiprocessing.Process(target=Master.masterTracker,args=(k,numberOfNodes, numberOfprocessesOfNodes,startingPortMasterClient,masterDataFile, dataKeepersState, syncLock, filesDictionary ,replicatesCount,iAmAliveDict)) 
        processes.append(t)
    for i in range(numberOfNodes):
        for k in range(numberOfprocessesOfNodes):
            t= multiprocessing.Process(target=DataKeeper.dataKeeper,args=(i,k,startingPortDatakeeperClient,numberOfprocessesOfMaster,masterIp)) 
            processes.append(t)

    print("Enter # of client processes:")
    numberOfClients=input()
    for i in range(int(numberOfClients)):
        commands=[]
        print("Enter # of commands for process #%d"%i)
        n=input()
        for j in range(int(n)):
            print("command #%d:"%j)
            x=input()
            commands.append(x)
        t=multiprocessing.Process(target=client.client,args=(masterIp,startingPortMasterClient,numberOfprocessesOfMaster,commands))
        processes.append(t)

    for j in processes:
        j.start()
        
    for j in processes:
        j.join()
    print("Done!")
    while(True):
        []