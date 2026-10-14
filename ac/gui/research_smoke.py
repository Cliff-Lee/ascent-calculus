"""Real native PP09 journey; callers must isolate ASCENT_ENGINE_DATA_DIR."""
import json
from pathlib import Path
import time
import tkinter as tk


def run_native_journey(pack=None):
    from ac.gui.desktop import DesktopWorkbench
    from ac.gui.research_jobs import jobs
    from ac.gui.research_library_model import database_path,library_search
    from tkinter import filedialog
    root=tk.Tk();app=DesktopWorkbench(root);root.update()
    started=time.monotonic()
    assert app.research_view is None, 'Research view must be lazy at startup'
    app._show_view('research');root.update();panel=app.research_view
    if pack:
        original=filedialog.askopenfilename
        try:
            filedialog.askopenfilename=lambda **_:str(pack)
            panel.import_pack();root.update()
        finally:filedialog.askopenfilename=original
        assert library_search()['available_count']==140
    panel.query.set('Baxter');panel.search();root.update()
    assert 'PP-129' in panel.works.get_children()
    panel.works.selection_set('PP-129');panel.select_work();root.update()
    detail=panel.details.get('1.0','end')
    assert 'C-PP-129-6' in detail and 'PROVED_EXTERNAL' in detail
    assert panel.current['citations'][panel.citations.current()]['url'].startswith('https://')
    position=next(i for i,c in enumerate(panel.current['capabilities']) if c['id']=='bijection')
    panel.methods.current(position);panel.run()
    deadline=time.monotonic()+20
    while panel.result is None and time.monotonic()<deadline:
        root.update();time.sleep(.02)
    assert panel.result is not None, panel.status.get()
    assert panel.result['finite_validation_status']=='finite_verified'
    output=panel.output.get('1.0','end')
    assert 'VERIFIED_TO_N' in output and '[1, 2, 3, 4]' in output and 'unproved' in output
    assert 'Counterexamples' in output and 'tile_size' in output
    panel.objects.current(0);panel.inspect();root.update()
    assert app.transform_word_var.get()=='1 1'
    assert 'base 0' in app.transform_help.cget('text')
    app._show_view('research');root.update();panel.run()
    cancelled=panel.job;before=time.monotonic();panel.cancel();root.update()
    assert jobs().poll(cancelled)['status']=='cancelled'
    cancel_seconds=time.monotonic()-before
    report={'native_window_mapped':bool(root.winfo_ismapped()),'lazy_startup':True,
            'pack_records':library_search()['available_count'],'source_citation':'C-PP-129-6',
            'method':'bijection','tested_degrees':panel.current['capabilities'][position]['degrees'],
            'counterexample_inspector_positive_word':[1,1],'source_base':0,
            'cancel_status':'cancelled','cancel_seconds':cancel_seconds,
            'journey_seconds':time.monotonic()-started,'proof_status':'unproved',
            'data_store':str(database_path())}
    jobs().close();root.destroy()
    return report
