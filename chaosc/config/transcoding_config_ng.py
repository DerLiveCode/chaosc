from chaosc.transcoders_ng import *

transcoders = [
    MappingTranscoder(
        "/(.*?)/ekg",
        "insert resolume osc address here",
        [["osc_arg", 0, "osc_arg", 0, IntRange2FloatConverter(1023)]]),
    MappingTranscoder(
        "/(.*?)/heartbeat",
        "insert resolume osc address here",
        [
            ["osc_arg", 0, "osc_arg", 0, KeepConverter()],
            ["osc_arg", 1, "osc_arg", 1, KeepConverter()],
            ["osc_arg", 2, "osc_arg", 2, KeepConverter()]]),
    MappingTranscoder(
        "/(.*?)/airFlow",
        "insert resolume osc address here",
        [
            ["osc_arg", 0, "osc_arg", 0, KeepConverter()]]),
    MappingTranscoder(
        "/(.*?)/emg",
        "insert resolume osc address here",
        [
            ["osc_arg", 0, "osc_arg", 0, KeepConverter()]]),
    MappingTranscoder(
        "/(.*?)/temperature",
        "insert resolume osc address here",
        [
            ["osc_arg", 0, "osc_arg", 0, KeepConverter()]]),
]
