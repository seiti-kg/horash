import os

yara_content = """import "pe"
import "math"

rule EICAR_Test {
    meta:
        description = "EICAR test file"
    strings:
        $eicar = "X5O!P%@AP[4\\\\PZX54(P^)7CC)7}EICAR-STANDARD-ANTIVIRUS-TEST-FILE!H+H*"
    condition:
        $eicar
}

rule PE_UPX_Packed {
    meta:
        description = "UPX packed PE"
    strings:
        $upx0 = "UPX0" ascii
        $upx1 = "UPX1" ascii
    condition:
        uint16(0) == 0x5A4D and all of them
}

rule PE_Suspicious_EntryPoint {
    meta:
        description = "PE com entry point suspeito"
    condition:
        uint16(0) == 0x5A4D and pe.number_of_sections > 0 and pe.entry_point_raw == 0
}

rule Ransomware_Generic {
    meta:
        description = "ransomware generico"
    strings:
        $note1 = "decrypt" nocase ascii wide
        $note2 = "ransom" nocase ascii wide
        $note3 = "bitcoin" nocase ascii wide
        $api1 = "CryptEncrypt" ascii wide
        $api2 = "CryptGenKey" ascii wide
    condition:
        2 of ($note*) and 1 of ($api*)
}

rule Powershell_Obfuscation {
    meta:
        description = "powershell ofuscado"
    strings:
        $a = "-enc" nocase ascii wide
        $b = "-EncodedCommand" nocase ascii wide
        $c = "Invoke-Mimikatz" nocase ascii wide
        $d = "DownloadString" nocase ascii wide
    condition:
        2 of them
}

rule Office_Macro_Suspicious {
    meta:
        description = "office macro suspeito"
    strings:
        $a = "AutoOpen" nocase ascii wide
        $b = "AutoExec" nocase ascii wide
        $c = "powershell" nocase ascii wide
    condition:
        2 of them
}

rule Webshell_Generic {
    meta:
        description = "webshell php"
    strings:
        $php1 = "eval($_POST" ascii wide
        $php2 = "eval($_GET" ascii wide
    condition:
        any of them
}

rule Double_Extension_Trick {
    meta:
        description = "dupla extensao"
    strings:
        $a = ".pdf.exe" nocase ascii wide
        $b = ".doc.exe" nocase ascii wide
    condition:
        any of them
}

rule Script_Dropper {
    meta:
        description = "dropper"
    strings:
        $a = "curl " ascii wide
        $b = "wget " ascii wide
        $c = "certutil -urlcache" nocase ascii wide
    condition:
        1 of them and filesize < 5MB
}

rule LNK_Suspicious {
    meta:
        description = "lnk suspeito"
    strings:
        $a = "powershell" nocase ascii wide
        $b = "cmd.exe" nocase ascii wide
    condition:
        uint16(0) == 0x4C00 and 1 of ($a,$b)
}

rule Miner_Generic {
    meta:
        description = "miner"
    strings:
        $a = "xmrig" nocase ascii wide
        $b = "stratum+tcp" nocase ascii wide
    condition:
        2 of them
}
"""

os.makedirs("yara/rules", exist_ok=True)
open("yara/rules.yar","w",encoding="ascii",newline="\n").write(yara_content)
open("yara/rules/curated.yar","w",encoding="ascii",newline="\n").write(yara_content)
print(f"written {len(yara_content)} bytes to yara/rules.yar")
# test
import subprocess, pathlib
try:
    r = subprocess.run(["yara/yara64.exe", "yara/rules.yar", "yara/yara64.exe"], capture_output=True, text=True, timeout=10)
    print("yara test rc:", r.returncode, "stdout:", r.stdout[:200], "stderr:", r.stderr[:200])
    if r.returncode not in (0,1):
        print("yara failed")
    else:
        print("yara ok")
except Exception as e:
    print("test err", e)
