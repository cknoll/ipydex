from colorama import Style, Back, Fore
import os


def hl(txt, k="g"):
    colors = {
        "g": Back.GREEN,
        "y": Back.YELLOW,
        "r": Back.RED,
    }

    start = colors[k]
    end = Style.RESET_ALL
    txt2 = txt.replace("\n", f"{end}\n{start}")

    return f"{start}{txt2}{end}"


def compare_strings(str1, str2, n=25):
    # Find the index of the first difference
    idx = next((i for i in range(min(len(str1), len(str2))) if str1[i] != str2[i]), None)

    if idx is None:
        if len(str1) == len(str2):
            print("The strings are identical.")
            return
        idx = min(len(str1), len(str2))

    # Calculate the start and end indices for context
    start = max(0, idx - n)
    end = min(max(len(str1), len(str2)), idx + n + 1)

    # Print the context
    print(f"First difference at index {idx}:")
    print(f"{str1[start:idx]}{hl(str1[idx:end], 'g')}")
    print(f"{str2[start:idx]}{hl(str2[idx:end], 'y')}")


def regex_a_in_b(a_pattern_str:str, b_target_str:str) -> bool:
    import re

    # DOTALL flag to allow . to match newlines
    # Check if the pattern matches anywhere in target

    pattern = re.escape(a_pattern_str).replace("__dot_star__", ".*")
    return bool(re.search(pattern, b_target_str, re.DOTALL))

    # return bool(regex.search(b))


def get_out_and_err_of_command(cmd, _input=None, env: dict = None, extra_env: dict = None, returncode=False):
    import subprocess
    import os

    if env is None:
        env = os.environ.copy()

    if extra_env is not None:
        env.update(extra_env)

    p = subprocess.Popen(cmd, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    out, err = p.communicate(_input)

    out = out.decode("UTF-8")
    err = err.decode("UTF-8")

    if returncode:
        return out, err, p.returncode
    return out, err

def get_clipboard_content():

    if os.environ.get("IPYDEX_UNITTEST_RUNNING"):
        return os.environ.get("IPYDEX_CLIPBOARD_MOCK", "")

    else:
        import pyperclip
        return pyperclip.paste()


def get_caller_frame(upcount=1):
    import inspect

    # Get the frame of the caller (`upcount` frames above the current frame),

    frame = inspect.currentframe()

    # + 1 to leave this frame (we usually want at least the grand-parent)
    i = upcount + 1
    while i > 0:
        if frame.f_back is None:
            msg = f"Unexpectedly reached to of frame-stack for {i=}"
            raise ValueError(msg)
        frame = frame.f_back
        i -= 1

    return frame

# TODO: create unittest (currently not so critical feature)
def get_file_name_of_caller(return_with_ext=False, full_path=True, upcount=1):
    """
    This function is intended to be called from an arbitrary module and return the name of that module
    """
    # Get the filename from the caller's frame
    caller_frame = get_caller_frame(upcount)
    fpath = caller_frame.f_code.co_filename

    if full_path:
        return os.path.abspath(fpath)

    # extract just the basename (filename without path)
    fname = os.path.basename(fpath)
    root, _ext = os.path.splitext(fname)
    if return_with_ext:
        return fname
    else:
        return root

# TODO: obsolete (not applicable in desired use case)
def _reload_module(path, mod_name="__proxy_module__"):
    """
    Reload the module specified by a given path on the filesystem
    """
    import importlib
    import importlib.util
    import sys

    # Convert path to absolute path
    abs_path = os.path.abspath(path)

    # Find the module in sys.modules that corresponds to this path
    module_to_reload = None
    for module_name, module in sys.modules.items():
        if hasattr(module, '__file__') and module.__file__:
            if os.path.abspath(module.__file__) == abs_path:
                module_to_reload = module
                break

    if module_to_reload is None:
        # If module not found in sys.modules, try to load it
        module_to_reload = _import_module_from_path(abs_path)
        return module_to_reload
    elif mod_name == "__main__":
        raise NotImplementedError()

    else:
        # Reload the existing module
        return importlib.reload(module_to_reload)

def _import_module_from_path(abs_path, mod_name="temp_module"):
    import importlib
    spec = importlib.util.spec_from_file_location(mod_name, abs_path)
    if spec is None:
        raise ImportError(f"Cannot create module spec from path: {abs_path}")
    module_to_reload = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module_to_reload)
    return module_to_reload

class ReloadManager:
    def __init__(self):
        self.abs_path_of_caller = None
        self.callers_globals = None

rm = ReloadManager()

def _prepare_reloading(additional_upcount=0):
    rm.abs_path_of_caller = get_file_name_of_caller(full_path=True, upcount=2 + additional_upcount)

    caller_frame = get_caller_frame(upcount=1 + additional_upcount)
    rm.callers_globals = caller_frame.f_globals

    # for debugging
    return rm

def reload_this_module(mode=None, mod_name="__proxy_module__"):
    """
    This function is intended to be called from an interactive ipython shell.
    """
    if rm.abs_path_of_caller is None:
        _prepare_reloading(additional_upcount=1)
        return
    if mode == "prepare_only":
        return
    mod = _import_module_from_path(rm.abs_path_of_caller, mod_name=mod_name)

    # Inject all public names into globals
    for name in getattr(mod, '__all__', dir(mod)):
        if not name.startswith('_'):
            rm.callers_globals[name] = getattr(mod, name)
    return mod
