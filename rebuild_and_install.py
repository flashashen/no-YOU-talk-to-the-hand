import subprocess, shutil, glob

# uninstall and clean
whls = glob.glob('dist/no_you_talk_to_the_hand-*-py2-none-any.whl')
for whl in whls:
    subprocess.call('pip uninstall {}'.format(whl), shell=True)
shutil.rmtree('dist')

# build and install
subprocess.call('python setup.py build', shell=True)
subprocess.call('python setup.py bdist_wheel', shell=True)
whl = glob.glob('dist/no_you_talk_to_the_hand-*-py2-none-any.whl')[0]
subprocess.call('pip install {}'.format(whl), shell=True)

