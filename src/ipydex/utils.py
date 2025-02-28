
from colorama import Style, Back, Fore


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
