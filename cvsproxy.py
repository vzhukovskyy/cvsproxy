import time, socket, re, os, sys, threading

BUFFER_SIZE = 4096
CACHE_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.cache')

def debug(s):
    #print s
    pass

def trace(s):
    #print s
    pass

def warn(s):
    print 'WARNING!',s

def info(s):
    print s

def log(s):
    print s

def error(s):
    print 'ERROR!!!',s

def extract_label(string):
    index = string.rfind('/')+2
    label = string[index:]
    #debug('label in'+string+'is'+label)
    return label

def create_file(label, filename):
    filepath = os.path.join(CACHE_ROOT, label, filename[1:])
    folder = os.path.dirname(filepath)

    if not os.path.exists(folder):
        os.makedirs(folder)
    with open(filepath, "w") as f:
        pass

#u=rw,g=rwx,o=rw 
pattern = re.compile('^u=[rwx]*,g=[rwx]*,o=[rwx]*$')
prev_lines = []

def process_data(stream):
    global prev_lines
    while True:
        line = stream.readLine()
        if line is None:
            break
        if pattern.match(line):
            next_line = stream.readLine()
            if next_line is None:
                warn('found match but no next line. Rewind and skip')
                stream.rewind(len(prev_lines[0])+len(prev_lines[1])+len(line)+3)
                break
            else:
                warn('found good match')
                info('-2: '+prev_lines[0])
                info('-1: '+prev_lines[1])
                info(' 0: '+line)
                info('+1: '+next_line)

                filename = prev_lines[0]
                label = extract_label(prev_lines[1])
                size = int(next_line)

                create_file(label, filename)

        prev_lines.append(line)
        if len(prev_lines) > 2:
            prev_lines = prev_lines[1:]

class Stream:
    def __init__(self):
        self.queue = ''
        self.pos = 0
        self.lock = threading.Lock()
    
    def add(self, data):
        self.lock.acquire()
        self.queue = self.queue+data
        # reduce queue from tail 
        self.queue = self.queue[self.pos:]
        self.pos = 0
        debug('--------------------- add ------------------------')
        debug('data: "'+data+'"')
        debug('queue: "'+self.queue+'"')
        self.lock.release()
    
    def readLine(self):
        self.lock.acquire()
        debug('----------------- readline -----------------------')
        debug('pos='+str(self.pos))
        debug('queue="'+self.queue+'"')

        eol_pos = self.queue.find('\n', self.pos)
        line = None
        if eol_pos >= 0:
            line = self.queue[self.pos:eol_pos]
            self.pos = eol_pos+1
            debug('-------------')
            debug('line="'+line+'"')
            debug('pos='+str(self.pos))
        else:
            debug('-------------')
            debug('line=None')
            debug('pos='+str(self.pos))
        self.lock.release()
        return line

    def rewind(self, count):
        self.lock.acquire()
        debug('------------------ rewind ------------------------')
        debug('pos before rewind: '+str(self.pos))
        debug('queue="'+self.queue+'"')
        self.pos -= count
        debug('pos after rewind: '+str(self.pos))
        self.lock.release()

        
    
def receiver_from_client(client_conn, server_conn):
    while True:
        trace('receiver_from_client: receiving')
        data = client_conn.recv(BUFFER_SIZE)
        if not data:
            trace('receiver_from_client: disconnected')
            break
        trace('receiver_from_client: received '+data)
        trace('receiver_from_client: sending '+data)
        server_conn.send(data)
        trace('receiver_from_client: sent '+data)

stream_from_server = Stream()

def receiver_from_server(client_conn, server_conn):
    while True:
        trace('receiver_from_server: receiving')
        data = server_conn.recv(BUFFER_SIZE)
        if not data:
            trace('receiver_from_server: disconnected '+data)    
            break
        trace('receiver_from_server: received "'+data+'"')

        stream_from_server.add(data)
        process_data(stream_from_server)

        trace('sender_to_server: sending '+data)
        client_conn.send(data)
        trace('sender_to_server: sent '+data)

def run_proxy(listening_host, listening_port, server_host, server_port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((listening_host, listening_port))
    s.listen(10)
    log('Proxy: waiting for clients at ' + listening_host + ':' + str(listening_port))

    try:
        while True:
            client_conn, client_addr = s.accept()
            log('Proxy: new client ' + client_addr[0] + ':' + str(client_addr[1]))

            server_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_conn.connect((server_host, server_port))
            
            upstream_pipe = threading.Thread(target=receiver_from_client, args=(client_conn,server_conn))
            upstream_pipe.daemon = True
            upstream_pipe.start()

            downstream_pipe = threading.Thread(target=receiver_from_server, args=(client_conn,server_conn))
            downstream_pipe.daemon = True
            downstream_pipe.start()
    except KeyboardInterrupt: 
        pass
    finally:
        log('Proxy: closing server socket')
        s.close()

def main():
    run_proxy('127.0.0.1', 2401, '10.23.144.145', 2401)
    exit(1)

main()

