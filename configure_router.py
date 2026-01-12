import socket
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import re

def get_all_local_ips():
    """Return all local IPv4 addresses."""
    ips = []
    try:
        # Use getaddrinfo to find all interface addresses
        # This is a cross-platform way to get some; pure interface iteration is harder in standard lib without netifaces
        # We'll try a common trick: bind to all and see, or just use the hostname
        hostname = socket.gethostname()
        for ip in socket.gethostbyname_ex(hostname)[2]:
            if not ip.startswith('127.'):
                ips.append(ip)
    except:
        pass
    
    # Fallback/Manual check for the known subnet if missed
    # (The user has 192.168.100.x)
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('192.168.100.1', 80))
        ip = s.getsockname()[0]
        s.close()
        if ip not in ips:
            ips.append(ip)
    except:
        pass
        
    return list(set(ips))

def discover_gateway():
    """Discover UPnP gateway using SSDP on all interfaces."""
    print("[*] Discovering UPnP Gateway...")
    ssdp_request = (
        'M-SEARCH * HTTP/1.1\r\n'
        'HOST: 239.255.255.250:1900\r\n'
        'MAN: "ssdp:discover"\r\n'
        'MX: 2\r\n'
        'ST: urn:schemas-upnp-org:device:InternetGatewayDevice:1\r\n'
        '\r\n'
    )
    
    local_ips = get_all_local_ips()
    print(f"    [*] Scanning interfaces: {', '.join(local_ips)}")
    
    for local_ip in local_ips:
        print(f"    [*] Trying interface {local_ip}...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(3)
        try:
            sock.bind((local_ip, 0))
            sock.sendto(ssdp_request.encode(), ('239.255.255.250', 1900))
            
            while True:
                try:
                    data, addr = sock.recvfrom(1024)
                    response = data.decode()
                    if 'LOCATION:' in response.upper():
                        location_match = re.search(r'LOCATION: (.*)', response, re.IGNORECASE)
                        if location_match:
                            location = location_match.group(1).strip()
                            print(f"        [+] Found gateway at {addr[0]} via {local_ip}")
                            sock.close()
                            return location, addr[0], local_ip
                except socket.timeout:
                    break
        except Exception as e:
            print(f"        [!] Error on {local_ip}: {e}")
        finally:
            sock.close()
    
    return None, None, None

def get_control_url(description_url):
    """Parse device description XML to find the control URL."""
    try:
        response = urllib.request.urlopen(description_url)
        xml_content = response.read()
        
        # Look for WANIPConnection or WANPPPConnection
        services = [
            'urn:schemas-upnp-org:service:WANIPConnection:1',
            'urn:schemas-upnp-org:service:WANPPPConnection:1'
        ]
        
        root = ET.fromstring(xml_content)
        ns = {'upnp': 'urn:schemas-upnp-org:device-1-0'}
        
        # This is a simplified search; robust XML parsing with namespaces can be tricky blindly
        # We'll treat it as string if namespace parsing fails or just iterate all elements
        
        content_str = xml_content.decode()
        
        for service_type in services:
            if service_type in content_str:
                # Find the service block
                # Very rough extraction to avoid complex namespace handling code for this snippet
                # Find <serviceType>...service_type...</serviceType> and then the sibling <controlURL>
                
                # A better way with regex for simplicity in a standalone script without knowing exact structure
                # (Some routers nest heavily)
                
                # Let's try to find the service element in the tree
                for service in root.findall(".//*{urn:schemas-upnp-org:device-1-0}service"):
                    s_type = service.find("*{urn:schemas-upnp-org:device-1-0}serviceType")
                    if s_type is not None and s_type.text == service_type:
                        control_url = service.find("*{urn:schemas-upnp-org:device-1-0}controlURL").text
                        return urllib.parse.urljoin(description_url, control_url), service_type
                        
                # Fallback purely string based if XML parsing was strict on namespace
                pass

    except Exception as e:
        print(f"    [!] Error parsing description XML: {e}")
    
    return None, None

def add_port_mapping(control_url, service_type, external_port, internal_client, internal_port, protocol='TCP'):
    """Send SOAP request to add port mapping."""
    print(f"[*] Attempting to forward External:{external_port} -> {internal_client}:{internal_port} ({protocol})")
    
    soap_body = f"""<?xml version="1.0"?>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
<s:Body>
<u:AddPortMapping xmlns:u="{service_type}">
<NewRemoteHost></NewRemoteHost>
<NewExternalPort>{external_port}</NewExternalPort>
<NewProtocol>{protocol}</NewProtocol>
<NewInternalPort>{internal_port}</NewInternalPort>
<NewInternalClient>{internal_client}</NewInternalClient>
<NewEnabled>1</NewEnabled>
<NewPortMappingDescription>OphthalmicsServer</NewPortMappingDescription>
<NewLeaseDuration>0</NewLeaseDuration>
</u:AddPortMapping>
</s:Body>
</s:Envelope>"""

    headers = {
        'Content-Type': 'text/xml',
        'SOAPAction': f'"{service_type}#AddPortMapping"'
    }
    
    try:
        req = urllib.request.Request(control_url, data=soap_body.encode(), headers=headers)
        urllib.request.urlopen(req)
        print("    [+] Port mapping added successfully!")
        return True
    except urllib.error.HTTPError as e:
        print(f"    [!] SOAP Request failed: {e.code} {e.reason}")
        print(f"    [!] Response: {e.read().decode()}")
        return False
    except Exception as e:
        print(f"    [!] Error adding port mapping: {e}")
        return False

def get_local_ip(target_ip):
    """Get local IP used to reach the gateway."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Doesn't need to be reachable
        s.connect((target_ip, 1))
        local_ip = s.getsockname()[0]
    except Exception:
        local_ip = '127.0.0.1'
    finally:
        s.close()
    return local_ip

def main():
    print("=== Automated Router Port Configuration ===")
    
    # 1. Discover
    location, gateway_ip, local_iface_ip = discover_gateway()
    if not location:
        print("[!] No UPnP Gateway found. Ensure UPnP is enabled on your router.")
        return

    # 2. Get Control Details
    print(f"[*] Getting control URL from {location}...")
    control_url, service_type = get_control_url(location)
    if not control_url:
        print("[!] Could not find valid WANIPConnection/WANPPPConnection service.")
        return

    print(f"    [+] Control URL: {control_url}")
    print(f"    [+] Service Type: {service_type}")

    # 3. Determine Local IP
    if local_iface_ip:
        local_ip = local_iface_ip
    else:
        local_ip = get_local_ip(gateway_ip)
    
    print(f"[*] Local IP detected: {local_ip}")

    # 4. Add Mapping
    success = add_port_mapping(control_url, service_type, 80, local_ip, 80, 'TCP')
    
    if not success:
        print("\n[!] Automatic configuration failed.")
        print("    This often happens if the ISP router has UPnP disabled or restricted.")
        print("    You may need to manually configure Port Forwarding in the specific web interface.")

if __name__ == "__main__":
    main()
