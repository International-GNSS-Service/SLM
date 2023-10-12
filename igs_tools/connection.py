from igs_tools.defines import DataCenter
from typing import Union, List
import ftplib
import requests
from bs4 import BeautifulSoup
import asyncio


class _FTPConnection:

    connection: ftplib.FTP

    # ftp only allows a single control channel - so we force ftp connections
    # to be serial
    lock_ = asyncio.Lock()

    def __init__(self, domain, username, password):
        self.connection = ftplib.FTP(domain)
        self.connection.login(user=username, passwd=password)

    async def list(self, directory: str) -> List[str]:
        async with self.lock_:
            try:
                self.connection.cwd(directory)
            except ftplib.error_perm as eperr:
                print(eperr)
                return []
            return self.connection.nlst()

    async def download(self, path: str):
        raise NotImplementedError(f'{self} must implement download()')


class _HTTPConnection:

    def __init__(self, domain, *args):
        self.domain = domain
        self.session = requests.session()

    async def list(self, directory: str) -> List[str]:
        raise NotImplementedError(f'{self} must implement list()')

    async def download(self, path: str):
        raise NotImplementedError(f'{self} must implement download()')


class _CDDISConnection(_HTTPConnection):

    async def list(self, directory: str) -> List[str]:
        try:
            filenames = []
            resp = requests.get(
                f'{self.domain.rstrip("/")}/{directory}'
            )
            if resp.status_code >= 400:
                print(f'Error: {resp.status_code} {resp.reason}')
                return []
            soup = BeautifulSoup(resp.content, 'html.parser')
            links = soup.find_all('a', {'class': 'archiveItemText'})
            for link in links:
                filenames.append(link.text)
            return filenames
        except Exception as err:
            print(err)
            return []


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
            if data_center == DataCenter.CDDIS:
                self._connection = _CDDISConnection(data_center.domain)
            else:
                raise NotImplementedError(
                    f'Connection for {data_center} not implemented.'
                )
        else:
            raise NotImplementedError(
                f'Protocol {data_center.protocol} not implemented.'
            )

    async def list(self, directory: str) -> List[str]:
        return await self._connection.list(directory)

    async def download(self, path: str):
        return await self._connection.download(path)
