import os,time


class Restart_counter:
    def __init__(self):
        self.restart_count_name = 'restart.count'
        self.lastValue = None


    def update(self,string):

        fid = open(self.restart_count_name,'w')
        fid.write(string)
        fid.close()


    def check(self):
        """
        Return True if correct restart count; False otherwise
        """

        if not os.path.isfile(self.restart_count_name):
            return False

        try:
            fid = open(self.restart_count_name)
            value = fid.read(-1)
            fid.close()
        except:
            return True

        if value == '':
            return True

        if self.lastValue is None:
            self.lastValue = value

            return True
        elif self.lastValue == value:
            return True
        else:
            return False

    def peek(self):
        if not os.path.isfile(self.restart_count_name):
            return ''

        try:
            fid = open(self.restart_count_name)
            value = fid.read(-1)
            fid.close()
        except:
            return ''


        return value

    def current_value(self):
        if self.lastValue is None:
            return ''
        else:
            return self.lastValue