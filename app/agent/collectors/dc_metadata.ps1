<#
Domain Controller Metadata Collector
#>

Import-Module ActiveDirectory

$metadata = @{}

# --- System Information ---
$os = Get-CimInstance Win32_OperatingSystem
$computer = Get-CimInstance Win32_ComputerSystem
$bios = Get-CimInstance Win32_BIOS

$metadata.system = @{
    hostname            = $env:COMPUTERNAME
    domain              = $computer.Domain
    domain_role         = $computer.DomainRole
    manufacturer        = $computer.Manufacturer
    model               = $computer.Model
    os_name             = $os.Caption
    os_version          = $os.Version
    os_build            = $os.BuildNumber
    last_boot_time      = $os.LastBootUpTime
    install_date        = $os.InstallDate
    serial_number       = $bios.SerialNumber
}

# --- AD Domain Information ---
$domain = Get-ADDomain
$forest = Get-ADForest

$metadata.active_directory = @{
    domain_name                 = $domain.DNSRoot
    netbios_name                = $domain.NetBIOSName
    forest_name                 = $forest.Name
    domain_mode                 = $domain.DomainMode
    forest_mode                 = $forest.ForestMode
    dc_functional_level         = $domain.DomainMode
}

# --- FSMO Roles ---
$metadata.fsmo_roles = @{
    schema_master          = $forest.SchemaMaster
    domain_naming_master   = $forest.DomainNamingMaster
    pdc_emulator           = $domain.PDCEmulator
    rid_master             = $domain.RIDMaster
    infrastructure_master  = $domain.InfrastructureMaster
}

# --- Installed Roles & Features ---
$roles = Get-WindowsFeature | Where-Object {$_.Installed -eq $true}

$metadata.installed_roles = $roles | Select-Object Name, DisplayName

# --- Critical Services ---
$services = Get-Service | Where-Object {$_.Status -eq "Running"}

$metadata.running_services = $services | Select-Object Name, DisplayName, StartType

# --- Network Configuration ---
$adapters = Get-NetIPAddress | Where-Object {$_.AddressFamily -eq "IPv4"}

$metadata.network = $adapters | Select-Object InterfaceAlias, IPAddress, PrefixLength

# --- Installed Software ---
$software = Get-ItemProperty HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\* |
    Select-Object DisplayName, DisplayVersion, Publisher, InstallDate

$metadata.installed_software = $software

# --- Security Baseline Info ---
$metadata.security = @{
    firewall_profiles = (Get-NetFirewallProfile | 
        Select-Object Name, Enabled)
    secure_boot       = (Confirm-SecureBootUEFI -ErrorAction SilentlyContinue)
}

# --- Output JSON ---
$metadata | ConvertTo-Json -Depth 6
