"""Command line entry for research ingestion and GitHub Pages publication."""
import argparse
from scanner import scan
from exporter import export

def main():
 p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='cmd',required=True)
 a=s.add_parser('scan');a.add_argument('--db',required=True)
 for opt in ('good','above-average','average','below-average','bad'):a.add_argument('--'+opt)
 a.add_argument('--profile-missing',action='store_true',help='Analyse external FLAC/MP3 files without existing audio JSON using GBR timeline DSP; slow first pass and requires librosa/numpy');a.add_argument('--catalogue',help='Existing GBR catalogue.json (optional)');a.set_defaults(func=scan)
 a=s.add_parser('export');a.add_argument('--db',required=True);a.add_argument('--output',required=True);a.set_defaults(func=export)
 a=p.parse_args();a.func(a)
