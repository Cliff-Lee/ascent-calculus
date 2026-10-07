from ac.gui.viewmodel import inspect_word, trace_gap_swap_repair, bounded_check, research_status

print("GUI-1 research workbench smoke")
print("==============================")
print("overall:", research_status()["overall"]["label"])
print("inspect 133122:", inspect_word("133122")["is_modified"])
trace = trace_gap_swap_repair("12321432")
print("trace:", trace["source"]["inspection"]["word"], "->", trace["gap_swap"]["output"]["inspection"]["word"], "->", trace["repair"]["output"]["inspection"]["word"])
check = bounded_check("m2122", "m2212", "repair21", 8)
print("bounded check:", check["title"])
