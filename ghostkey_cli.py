"""
GhostKey Sovereign Node CLI v1.0
Unified management utility for autonomous verification nodes.
Architect: Sahil Ahmad
"""

import sys
import argparse
from node_daemon import SovereignNodeDaemon
from node_client import run_peer_handshake
from gossip_engine import GhostKeyLedger

def main():
    parser = argparse.ArgumentParser(description="GhostKey Autonomous Node CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Command: start-node
    parser_start = subparsers.add_parser("start-node", help="Start the sovereign P2P verification node")
    parser_start.add_argument("--port", type=int, default=9000, help="Listening port (default: 9000)")
    parser_start.add_argument("--id", type=str, default="PEER-SOVEREIGN-NODE", help="Node identifier")

    # Command: test-handshake
    parser_test = subparsers.add_parser("test-handshake", help="Execute hardware handshake against local node")
    parser_test.add_argument("--port", type=int, default=9000, help="Target node port")

    # Command: audit-ledger
    subparsers.add_parser("audit-ledger", help="Verify cryptographic integrity of local ledger chain")

    args = parser.parse_args()

    if args.command == "start-node":
        print(f"[⚡] Starting GhostKey Node on port {args.port}...")
        node = SovereignNodeDaemon(port=args.port, node_id=args.id)
        node.start()

    elif args.command == "test-handshake":
        print(f"[🔍] Running peer handshake against localhost:{args.port}...")
        try:
            run_peer_handshake(port=args.port)
        except ConnectionRefusedError:
            print("[❌] Error: Target node is offline. Run 'start-node' first.")

    elif args.command == "audit-ledger":
        ledger = GhostKeyLedger()
        valid, msg = ledger.verify_chain_integrity()
        print(f"[✓] Ledger Integrity Status: {valid} ({msg})")

    else:
        parser.print_help()

if __name__ == "__main__":
    main()
