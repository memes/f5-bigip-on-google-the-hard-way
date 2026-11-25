// Proxy configuration for BIG-IP on Google Cloud the hard way that uses a local SOCKS proxy (ssh -D 8080) to tunnel
// connections intended for private management IP addresses.
// Source: https://github.com/memes/f5-bigip-on-google-the-hard-way/blob/main/big-ip-the-hard-way.pac
function FindProxyForURL(url, host) {
  if (isInNet(host, '10.100.0.0', '255.255.0.0')) {
    return 'SOCKS localhost:8080';
  }
  return "DIRECT";
}
