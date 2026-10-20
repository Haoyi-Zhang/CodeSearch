"""Check the exact retained publisher files without modifying either file."""
from pathlib import Path
import hashlib
def validate_publisher_files(paper):
    paper=Path(paper)
    for name,expected in [('acmart.cls','815eb82e1a2496a21a3f01d00b6945d865271403'),
                          ('ACM-Reference-Format.bst','4f607da45ff04d5712f87a7a3308507dab41fac3')]:
        b=(paper/name).read_bytes()
        blob=hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
        if blob!=expected:raise ValueError('publisher file modified: '+name)
