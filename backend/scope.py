import ipaddress
import re
from urllib.parse import urlsplit


def hostname(value: str) -> str:
    """Offline parsing only. No resolution, connections, paths, credentials or ports."""
    value = value.strip().lower().rstrip('.')
    if '://' in value:
        parsed = urlsplit(value)
        if parsed.scheme not in ('http', 'https') or parsed.username or parsed.password:
            raise ValueError('Use HTTP(S) sem credenciais, ou um hostname/IP.')
        if parsed.port not in (None, 80, 443) or parsed.path not in ('', '/') or parsed.query or parsed.fragment:
            raise ValueError('Escopo desta versão aceita hosts inteiros; não URLs com caminho, porta, query ou fragmento.')
        value = (parsed.hostname or '').rstrip('.')
    try:
        return str(ipaddress.ip_address(value))
    except ValueError:
        pass
    value = value.encode('idna').decode('ascii')
    if len(value) > 253 or not re.fullmatch(r'[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?', value):
        raise ValueError('Hostname inválido.')
    if any(not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?', label) for label in value.split('.')):
        raise ValueError('Hostname inválido.')
    return value


def pattern(value: str) -> str:
    if value.startswith('*.'):
        host = hostname(value[2:])
        try:
            ipaddress.ip_address(host)
        except ValueError:
            if '.' not in host:
                raise ValueError('Wildcard exige domínio completo.')
            return '*.' + host
        raise ValueError('Wildcard não aceita IP.')
    return hostname(value)


def matches(host: str, rule: str) -> bool:
    return host.endswith('.' + rule[2:]) if rule.startswith('*.') else host == rule


def check(program, assets, target: str) -> dict:
    host = hostname(target)
    if not program.authorized or not program.authorization:
        return {'allowed': False, 'host': host, 'reason': 'Programa sem autorização registrada.'}
    matched = [asset for asset in assets if matches(host, asset.pattern)]
    if any(not asset.allowed for asset in matched):
        return {'allowed': False, 'host': host, 'reason': 'Regra de proibição tem precedência.'}
    if any(asset.allowed for asset in matched):
        return {'allowed': True, 'host': host, 'reason': 'Host coberto por regra permitida. Consulte também as condições do programa.'}
    return {'allowed': False, 'host': host, 'reason': 'Host sem permissão explícita (bloqueio por padrão).'}
