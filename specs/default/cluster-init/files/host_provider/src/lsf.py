class MachineStates:
    building = "building"
    active = "active"
    error = "error"
    deleting = "deleting"
    deleted = "deleted"
    
    
class MachineResults:
    succeed = "succeed"
    executing = "executing"
    failed = "failed"
    
    
class RequestStates:
    running = "running"
    complete = "complete"
    complete_with_error = "complete_with_error"
