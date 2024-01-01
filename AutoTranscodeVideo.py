import subprocess
import os
import subprocess
import psutil
import pathlib
import ffmpeg
import concurrent.futures
from send2trash import send2trash


def get_file_list(path):
    """
    获取指定路径下的文件列表，仅包括后缀为.mp4、.mov、.mkv、.avi的文件，并按照修改时间进行排序。

    参数:
    path (str): 文件路径

    返回:
    list: 按照修改时间排序的文件列表
    """
    files = [p.resolve() for p in pathlib.Path(path).glob("**/*") if p.suffix in {".mp4", ".mov", ".mkv", ".avi"}]
    return sorted(files, key=lambda file: file.stat().st_mtime)
    # return sorted(files, key=lambda file: file.stat().st_size)


def get_video_file_info(file):
    # 使用ffmpeg的ffprobe命令获取文件的详细信息
    ffprobe_output = ffmpeg.probe(file, cmd='H:\\Programs\\ffmpeg\\ffprobe.exe')

    # 获取媒体的格式信息
    media_format = ffprobe_output['format']

    # 获取视频流信息
    video_stream = [stream for stream in ffprobe_output['streams'] if stream['codec_type'] == 'video'][0]

    # 获取音频流信息
    audio_stream = [stream for stream in ffprobe_output['streams'] if stream['codec_type'] == 'audio'][0]

    # 返回媒体格式、视频流和音频流信息
    return media_format, video_stream, audio_stream


def transcode_video(src: pathlib.Path, dst: pathlib.Path):
    print(f'Transcoding {src.__str__()} to {dst.__str__()}')

    my_env = os.environ.copy()
    my_env["FFREPORT"] = f'file={dst.name}.log:level=32'

    command = [f'H:\\Programs\\ffmpeg\\ffmpeg.exe',
               '-hwaccel', 'auto',
               f'-i', f'{src.__str__()}',
               f'-f', f'matroska',
               f'-b:a', f'192k',
               f'-c:a', f'aac',
               f'-c:s', f'mov_text',
               f'-c:v', f'libx265',
               f'-crf', f'28',
               f'-x265-params', f'crf=28',
               f'-movflags',
               f'+faststart',
               f'-pix_fmt', 'yuv420p',
               f'-preset', 'medium',
               f'-threads', '0',
               f'-vf', 'scale=trunc(iw/2)*2:trunc(ih/2)*2',
               f'{dst.__str__()}',
               f'-fps_mode', '2',
               f'-map', '0:v:0?',
               f'-map', '0:a?',
               f'-map', '0:s?',
               f'-v', 'quiet',
               f'-hide_banner',
               f'-report',
               f'-stats',
               ]

    process = subprocess.Popen(command, env=my_env)

    try:
        # 使用 psutil 设置 I/O 优先级为 'IOPRIO_CLASS_IDLE'，即非常低
        print(f'set IOPRIO_LOW to pid: {process.pid}')
        p = psutil.Process(process.pid)
        p.ionice(psutil.IOPRIO_LOW)
        p.nice(psutil.IDLE_PRIORITY_CLASS)
    except Exception as e:
        print(f"Error setting ionice level: {e}")

    process.communicate()
    return_code = process.returncode
    return return_code


def compare_float(a, b) -> bool:
    a = float(a)
    b = float(b)
    absolute_difference = abs(a - b)
    larger_number = max(abs(a), abs(b))
    if larger_number == 0:
        return False
    else:
        return absolute_difference / larger_number <= 0.01


def process_video_file(src: pathlib.Path):
    src_m, src_v, src_a = get_video_file_info(src)
    if src_v['codec_name'] == 'hevc':
        dst = pathlib.Path('F:\\output\\').joinpath(src.name)
        if not dst.exists():
            src.rename(dst)
    else:
        transcode = True
        dst = pathlib.Path('F:\\output\\').joinpath(f'{src.stem}.mkv')
        if dst.exists():
            try:
                dst_m, dst_v, dis_a = get_video_file_info(
                    dst)  # 调用 get_video_file_info(dst) 函数获取目标文件的信息，并将返回的结果分别赋值给变量 dst_m、dst_v 和 dis_a
                if not compare_float(src_m['duration'], dst_m['duration']):  # 如果目标文件的时长与源文件的时长不相等
                    print(f'Error: {dst.__str__()} duration is not equal to {src.__str__()}')  # 打印错误信息
                    print(f'{src_m["duration"]} vs {dst_m["duration"]}')
                    print(f'Deleting {dst.__str__()}')  # 打印删除目标文件的信息
                    send2trash(dst)
                else:  # 如果目标文件的时长与源文件的时长相等
                    src.rename(pathlib.Path("F:\\trash").joinpath(src.name))  # 将源文件重命名为垃圾文件
                    transcode = False  # 设置转码标记为 False
            except (KeyError, Exception):  # 如果发生异常（ EITHER KeyError OR Exception ）
                print(f'Error: {dst.__str__()} is not a valid video file')  # 打印错误信息
                print(f'Deleting {dst.__str__()}')  # 打印删除目标文件的信息
                send2trash(dst)
        if transcode:  # 如果需要转码
            return transcode_video(src, dst)
    return False


def main():
    file_list = get_file_list("F:\\input\\")

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:  # 使用线程池执行任务，最大线程数为3
        for _ in executor.map(process_video_file, file_list):  # 遍历所有任务的执行结果
            pass  # 空循环，表示任务执行完毕
        print('Done')


if __name__ == '__main__':
    main()
