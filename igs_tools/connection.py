from igs_tools.defines import DataCenter
from typing import Union, List
import ftplib


class _FTPConnection:

    connection: ftplib.FTP

    def __init__(self, domain, username, password):
        self.connection = ftplib.FTP(domain)
        self.connection.login(user=username, passwd=password)

    def list(self, directory: str) -> List[str]:
        try:
            self.connection.cwd(directory)
        except ftplib.error_perm as eperr:
            print(eperr)
            return []
        return self.connection.nlst()


class _HTTPConnection:
    pass


class Connection:

    data_center: DataCenter
    username: str
    password: str

    def __init__(self, data_center: DataCenter, username='', password=''):
        self.data_center = data_center
        self.username = username or ''
        self.password = password or ''
        if data_center.protocol == 'ftp':
            self._connection = _FTPConnection(
                data_center.domain,
                self.username,
                self.password
            )
        elif data_center.protocol in ['http', 'https']:
            # TODO
            pass
        else:
            raise NotImplementedError(
                f'Protocol {data_center.protocol} not implemented.'
            )

    def list(self, directory: str) -> List[str]:
        return self._connection.list(directory)

    def download(self, path: str):
        pass
