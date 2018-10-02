from pythonlsf import lsf
from collections import OrderedDict


class LsfError(RuntimeError):
    pass


class LsfArray:
    '''
    Ease of use wrapper around supported lsf arrays.
    > lsf_arr = LsfArray([1,2,3], "int")
    > lsf_arr[1] = lsf_arr[0] * 2
    > lsf.some_func(lsf_arr.native)
    > lsf_arr.delete()
    
    '''
    
    def __init__(self, pointer, length, type_name):
        self.deleter = getattr(lsf, "delete_%sArray" % type_name)
        self.setter = getattr(lsf, "%sArray_setitem" % type_name)
        self.getter = getattr(lsf, "%sArray_getitem" % type_name)
        if pointer is not None:
            self.length = length
            self.native = pointer
        else:
            self.length = 0
            self.native = None
    
    @classmethod     
    def from_list(cls, pylist, type_name):
        length = len(pylist)
        allocator = getattr(lsf, "new_%sArray" % type_name)
        native = allocator(length)
        ret = LsfArray(native, length, type_name)
        for n, item in enumerate(pylist):
            ret[n] = item
        return ret
        
    def delete(self):
        self.deleter(self.native)
        self.native = None
        
    def __iter__(self):
        
        class _Iter:
            def __init__(self, lsf_array):
                self.__lsf_array = lsf_array
                self.__index = 0
                self.__length = lsf_array.length
            
            def next(self):
                if self.__index < self.__length:
                    ret = self.__lsf_array[self.__index]
                    self.__index = self.__index + 1
                    return ret
                raise StopIteration()
            
        return _Iter(self)
            
    def __setitem__(self, n, item):
        assert n < len(self)
        self.setter(self.native, n, item)
        
    def __getitem__(self, n):
        return self.getter(self.native, n)
    
    def __len__(self):
        return self.length
    
    def __del__(self):
        self.delete()



class LsfWrapper:
    '''
    Library level wrapper around pythonlsf.lsf's
    '''
    
    def __init__(self):
        if lsf.lsb_init(None) < 0:
            raise LsfError
    
    def lsb_queueinfo(self, queues=[], hosts=None, user=None, bitwise_options=0):
        lsf_queues = LsfArray.from_list(queues, "string")
        
        num_queues_out = lsf.new_intp()
        lsf.intp_assign(num_queues_out, len(queues))
        
        lsf_hosts = LsfArray.from_list(hosts, "string")
        
        _queue_info_ents = lsf.lsb_queueinfo(lsf_queues.native, num_queues_out, lsf_hosts.native, user, bitwise_options)
        
        if _queue_info_ents is None:
            raise LsfError("lsb_queueinfo(%s, %s, %s, %s)" % (queues, hosts, user, bitwise_options))
        
        num_queues = lsf.intp_value(num_queues_out)
        
        if num_queues == 0:
            raise LsfError("No queues matched queues=%s hosts=%s user=%s and options=%d" % (queues, hosts, user, bitwise_options))
        return _queue_info_ents
    
    def lsb_readjobinfo(self, user="all", bitwise_options=0):
        
        if lsf.lsb_openjobinfo(0, None, user, None, None, bitwise_options) < 0:
            # not an error, there just aren't any jobs
            return []
        
        more = None
        try:
            more = lsf.new_intp()
            lsf.intp_assign(more, 1)
            while lsf.intp_value(more):
                job = lsf.lsb_readjobinfo(more)
                if job is None:
                    raise LsfError("lsb_readjobinfo")
                
                print "parse(JobId: %d User:%s Request:%s)" % (job.jobId, job.user, job.combinedResReq)
            
        finally:
            if more:
                lsf.delete_intp(more)
            lsf.lsb_closejobinfo()
    
    lsb_userinfo2_fields = ["user", "procJobLimit", "maxJobs", "numStartJobs", "numJobs", "numPEND", "numSSUSP", "numUSUSP", "numRESERVE", "maxPendJobs"]       
    
    def lsb_userinfo2(self):
        num_users_out = lsf.new_intp()
        lsf.intp_assign(num_users_out, 0)
        
        _userinfo = lsf.lsb_userinfo2(None, num_users_out, 0)
        num_users = lsf.intp_value(num_users_out)
        if num_users <= 0:
            raise LsfError("lsb_userinfo2 - num_users=%d" % num_users)
        
        lsf.delete_intp(num_users_out)
        
        recs = []
        for userinfo in LsfArray(_userinfo, num_users, "userInfoEnt"):
            rec = OrderedDict()
            for field in self.lsb_userinfo2_fields:
                rec[field] = getattr(userinfo, field)
            recs.append(rec)
        return {"USERS": recs}
