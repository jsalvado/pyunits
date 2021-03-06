import numpy as np
import os

COMPARISON_UFUNC = {np.greater, np.greater_equal, np.less, np.less_equal, np.not_equal, np.equal}
UNITLESS_UFUNC   = {np.sin, np.cos, np.exp, np.arcsin, np.arccos, np.tan, np.arctan, np.log, np.log10}

class UnitError(Exception) : pass
repcal = False
def search(st):
    cmd="echo \"search " + st +"\" | units "
    out=os.popen(cmd)
    print(out.read().split("You have: ")[1])


class phval(np.ndarray):
    def __new__(cls, input_array=None, units=None):
        name=None
        if isinstance(input_array,str) and units==None:
            units=input_array
            input_array=np.array(1.)
        if isinstance(units, int):
            units = units
            obj   = input_array
        elif isinstance(units, str):
            name=units
            val, pw = cls.strunit(1., units)
            obj     = np.multiply(input_array, val)
            units   = pw
        else:
            raise UnitError("Not possible to create the units instance")

        obj = np.asarray(obj).view(cls)
        obj.units = units
        obj.name = name
        cls.use_units=True
        return obj

    @classmethod
    def turn_of_units(cls):
        cls.use_units = False

    @property
    def values(self):
        return self.view(np.ndarray)

    def val_u(self, uname):
        if isinstance(uname,str):
            un=phval(1., uname)
        elif isinstance(uname,phval):
            un=uname
        else:
            raise UnitError("val_u: Argument must be a string or phval")

        if un.units == self.units:
            return (self/phval(1., uname)).view(np.ndarray)
        else:
            raise UnitError("val_u: Wrong units to show the value")
        
            
        
    @staticmethod
    def strunit(a,st):
        """It returs the arguments for the phval initialization with values "a" and units given 
        by the string "st" """
        cmd="units -u natural "
        out=os.popen(cmd + "\"" + st + "\"").read()
        
        if not "eV" in out:
            out=out.split()
            #print(out)
            return (a*float(out[-1]), 0)
        else:
            out=out.split()
        
        if out[-2]=="/":
            return (a*float(out[-3]), -1 if len(out[-1].split("^"))<2 else -int(out[-1].split("^")[-1]))
        else:
            return (a*float(out[-2]), 1 if len(out[-1].split("^"))<2 else int(out[-1].split("^")[-1]))

        
    def __repr__(self):
        if repcal:
            if self.units == 0:
                return  (self.values.__str__())
            else:
                return  (self.values.__str__()) + " eV^"+str(self.units)
        else:
            return  (self.values.__repr__()) + " eV^"+str(self.units)

    def __str__(self):
        return  (self.values.__str__()) + " eV^"+str(self.units)

    def str(self, unit):
        """returns the value with the units labeled by the string "unit" """
        if isinstance(unit, str):
            un=phval(1,unit)
        elif isinstance(unit, phval) and  isinstance(unit.name,str):
            un=unit
            unit=un.name
        else:
            raise unitError("Argument should be a string or phval with name")

        if self.units==un.units:
            return str((self/un).view(np.ndarray)) +" "+ unit
        else:
            raise UnitError("Invalit units")

    
    def __getitem__(self, indx):
        return phval(self.values[indx], self.units)

    __array_priority__ = 1000

    def __array_ufunc__(self, ufunc, method, *inputs, **kwargs):
        def get_units(obj):
            if isinstance(obj, phval):
                return obj.units
            elif isinstance(obj, (list, tuple)):
                #check all units the same
                units = np.unique(tuple(map(get_units, obj)))
                if len(units) > 1:
                    raise UnitError('Operation with mixed units are not supported')
                else:
                    unit = units[0]
                return unit
            else : return 0

        def get_casted(obj):
            if isinstance(obj, phval):
                return obj.view(np.ndarray)
            elif isinstance(obj, (list, tuple)):
                return np.array(tuple(map(get_casted, obj)))
            else : return obj

        list_inputs = list(inputs)
        list_units = [int(get_units(inp)) for inp in inputs]
        casted_inputs = [get_casted(inp) for inp in inputs]

        if self.use_units:

            if ufunc == np.power:
                if list_units[1] != 0:
                    raise UnitError("power: not units allowed in the exponend, divide by something!")
                elif list_units[0]==0:
                    return phval(ufunc(*casted_inputs), units=0)
                if np.isscalar(casted_inputs[1]):
                    units = list_units[0]*casted_inputs[1]
                    if ((units-int(units))==0):
                        return phval(ufunc(*casted_inputs), units=int(units))
                    else:
                        raise UnitError("Only integer powers of units are valid")
                elif np.all(casted_inputs[1]==casted_inputs[1][0]):
                    units = list_units[0]*casted_inputs[1][0]
                    if ((units-int(units))==0):
                        return phval(ufunc(*casted_inputs), units=int(units))
                    else:
                        raise UnitError("Only integer powers of units are valid")
                else:
                    raise UnitError("power: all the phval should have the same units")

            if ufunc == np.square:
                units = list_units[0] * 2
                return phval(ufunc(*casted_inputs), units=units)

            if ufunc == np.sqrt:
                if list_units[0]%2==0:
                    units = int(list_units[0]/2)
                    return phval(ufunc(*casted_inputs), units=units)
                else:
                    raise UnitError("SQRT failed, output units must be an integer power")
                

            if ufunc in UNITLESS_UFUNC:
                units = list_units[0]
                if units==0:
                    return phval(ufunc(*casted_inputs), units=units)
                else:
                    raise UnitError("This is a unitless fucntion, divide by some physical scale!")


            if ufunc == np.negative:
                return phval(ufunc(*casted_inputs), units=list_units[0])

            if ufunc in COMPARISON_UFUNC.union([np.add, np.subtract]):
                if (list_units[0] == list_units[1]) or any(np.all(inputs == 0) for inputs in casted_inputs):
                    return phval(ufunc(*casted_inputs), units=list_units[0])
                else:
                    raise UnitError("Can't compare non-zero values with different units!")
            if ufunc == np.multiply:
                units = list_units[0] + list_units[1]
                return phval(ufunc(*casted_inputs), units=units)

            if ufunc == np.divide:
                units = list_units[0] - list_units[1]
                return phval(ufunc(*casted_inputs), units=units)

            else:
                raise UnitError("ufunc error")
        else:
            return  ufunc(*casted_inputs)

    def __array_finalize__(self, obj):
        if obj is None: return
        self.units = getattr(obj, 'units', None)
