from anyio import open_file
from fastapi import UploadFile

from backend.common.enums import FileType
from backend.common.exception import errors
from backend.common.log import log
from backend.core.conf import settings
from backend.core.path_conf import UPLOAD_DIR
from backend.utils.timezone import timezone


def build_filename(file: UploadFile) -> str:
    """
    Build the filename

    :param file: FastAPI upload file object
    :return:
    """
    timestamp = int(timezone.now().timestamp())
    filename = file.filename
    file_ext = filename.split('.')[-1].lower()
    new_filename = f'{filename.replace(f".{file_ext}", f"_{timestamp}")}.{file_ext}'
    return new_filename


def upload_file_verify(file: UploadFile) -> None:
    """
    Validate the file

    :param file: FastAPI upload file object
    :return:
    """
    filename = file.filename
    file_ext = filename.split('.')[-1].lower()
    if not file_ext:
        raise errors.RequestError(msg='Unknown file type')

    if file_ext == FileType.image:
        if file_ext not in settings.UPLOAD_IMAGE_EXT_INCLUDE:
            raise errors.RequestError(msg='This image format is not supported yet')
        if file.size > settings.UPLOAD_IMAGE_SIZE_MAX:
            raise errors.RequestError(msg='Image exceeds the maximum size limit, please choose another one')
    elif file_ext == FileType.video:
        if file_ext not in settings.UPLOAD_VIDEO_EXT_INCLUDE:
            raise errors.RequestError(msg='This video format is not supported yet')
        if file.size > settings.UPLOAD_VIDEO_SIZE_MAX:
            raise errors.RequestError(msg='Video exceeds the maximum size limit, please choose another one')


async def upload_file(file: UploadFile) -> str:
    """
    Upload the file

    :param file: FastAPI upload file object
    :return:
    """
    filename = build_filename(file)
    try:
        async with await open_file(UPLOAD_DIR / filename, mode='wb') as fb:
            while True:
                content = await file.read(settings.UPLOAD_READ_SIZE)
                if not content:
                    break
                await fb.write(content)
    except Exception as e:
        log.error(f'Failed to upload file {filename}: {e!s}')
        raise errors.RequestError(msg='Failed to upload file')
    await file.close()
    return filename
