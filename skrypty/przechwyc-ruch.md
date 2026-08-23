# Gate O-1: packet capture as the final proof

**A condition of admitting the system to real case files.**

This gate inspects neither configuration nor code. It observes reality at the packet level. Every other safeguard can be misjudged; this one cannot.

## Criterion

During a **full document processing cycle**, not **a single packet** leaves the Docker network from the bridges of the `net_app`, `net_ai` and `net_parse` segments.

A full cycle means: upload, conversion, OCR, parsing, embedding, indexing, query, and an answer with citations.

## Preparation

1. **Disconnect the machine from the internet physically**: unplug the cable, switch off Wi-Fi. Do not rely on a firewall rule, because we are testing the system rather than our own configuration skills.
2. Start the stack and wait for it to settle, that is until services stop restarting.
3. Prepare a document from the synthetic corpus that has **not been processed before**, because a document already indexed will not exercise the whole path.

## Execution

Find the bridge names:

```bash
docker network ls --filter name=kancelaria-lex --format "{{.Name}} {{.ID}}"
```

Start a capture on each bridge, in separate terminals, using `br-<ID>`:

```bash
sudo tcpdump -i br-<ID> -w /tmp/lex-net_app.pcap -n
```

Run the full cycle through the interface, then stop the captures.

## Analysis

Filter out intra-segment traffic and see whether anything is left:

```bash
tcpdump -r /tmp/lex-net_app.pcap -n "not net 172.16.0.0/12 and not net 192.168.0.0/16 and not net 10.0.0.0/8"
```

Separately, look for outbound DNS queries:

```bash
tcpdump -r /tmp/lex-net_parse.pcap -n "udp port 53"
```

## Assessment

| Result | Meaning |
|---|---|
| Zero packets on every bridge | **Gate passed** |
| Traffic to private addresses | Internal traffic, which is fine |
| **Any packet to a public address** | **Stop the deployment.** Follow the "suspected outbound connection" path in [`../docs/operations/incident-response.md`](../docs/operations/incident-response.md) |
| **A DNS query for an external name** | Treat it as above. The query alone confirms that something tried to connect |

## A note on the gotenberg variant

Run the cycle **also on a file containing a linked external resource**, such as an image with a URL or an XML entity. That is a direct test of threat I-2: LibreOffice can try to fetch such a resource, and a letter from the opposing party with a linked image would become a read receipt at an address they control.

Prepare the test file yourself, with an address in the `.invalid` domain, so the attempt is unmistakable in the capture.

## Recording the result

**`.pcap` files can contain document content.** They are excluded from the repository (`.gitignore`) and are subject to the same rules as case files.

What goes into the journal (`infra/dziennik-zmian.md`): the date, the system version, the result and the name of the person who ran it. Keep the capture file itself as privileged material, or delete it after the analysis.
