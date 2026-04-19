import dns.message
import dns.query
import dns.rdatatype


def build_messages(config: dict) -> list[bytes]:
    messages = []
    for rdtype in config["rdatatypes"]: 
        msg = dns.message.make_query(
            qname=config["domain"],
            rdtype=dns.rdatatype.from_text(rdtype),
            use_edns=True,
            payload=1232,
        )
        msg.flags &= ~dns.flags.RD
        messages.append(msg.to_wire())
    return messages
