import "pe"
rule EICAR_Test {
    strings:
        $eicar = "X5O!P%@AP[4\\PZX54(P^)7CC)7}\$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!\$H+H*"
    condition:
        $eicar
}
rule Suspicious_Heavy_File {
    condition:
        filesize > 650MB
}
rule Generic_Malware_Strings {
    strings:
        $a = "malware" nocase
        $b = "keylogger" nocase
        $c = "ransom" nocase
    condition:
        any of them
}
