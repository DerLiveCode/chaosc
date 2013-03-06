from chaosc.transcoders import *

transcoders = [
    #AddressRegExChanger("/client(\d+)/(\d+)", "/massive%d/osc%d/freq"),
    #DampValue("/massive(\d+)/osc(\d+)/freq", 0.5),
    MidiChanger(
        "/1/fader(\d+)",
        "/midi/cc",
        [
            ["member", "channel", "osc_arg", 0, "int"],
            ["regex", 0, "osc_arg", 1, "int"],
            ["osc_arg", 0, "osc_arg", 2, "midi"]
        ],
        channel=0)
]
