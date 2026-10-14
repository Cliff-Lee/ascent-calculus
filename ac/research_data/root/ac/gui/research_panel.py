"""Lazy native Research Library view inside the existing desktop workbench."""
import json
import tkinter as tk
from tkinter import ttk,filedialog
import webbrowser
from ac.gui.research_library_model import library_search,work_detail,import_library,inspect_reference_word,STATUS_HELP,detail_text,result_text
from ac.gui.research_jobs import jobs


class ResearchPanel(ttk.Frame):
    def __init__(self,parent,app):
        super().__init__(parent,padding=12)
        self.app=app;self.current=None;self.job=None;self.result=None;self.after_token=None
        self.columnconfigure(0,weight=1);self.rowconfigure(2,weight=1);self.rowconfigure(4,weight=1)
        ttk.Label(self,text='Research Library · Benchmark / Method Explorer',font=('TkDefaultFont',14,'bold')).grid(row=0,column=0,sticky='w')
        controls=ttk.Frame(self);controls.grid(row=1,column=0,sticky='ew',pady=8)
        self.query=tk.StringVar();self.author=tk.StringVar();self.year=tk.StringVar();self.priority=tk.StringVar(value='Any')
        for label,variable in (('Search methods / families / relevance',self.query),('Author',self.author),('Year',self.year)):
            ttk.Label(controls,text=label).pack(side='left',padx=(0,4))
            entry=ttk.Entry(controls,textvariable=variable,width=25 if variable is self.query else 12);entry.pack(side='left',padx=(0,8));entry.bind('<Return>',lambda _:self.search())
        ttk.Combobox(controls,textvariable=self.priority,values=('Any','P0','P1','P2'),state='readonly',width=6).pack(side='left',padx=4)
        ttk.Button(controls,text='Search',command=self.search).pack(side='left')
        ttk.Button(controls,text='Import conference ZIP',command=self.import_pack).pack(side='left',padx=6)
        body=ttk.Panedwindow(self,orient='horizontal');body.grid(row=2,column=0,sticky='nsew')
        left=ttk.Frame(body);right=ttk.Frame(body);body.add(left,weight=1);body.add(right,weight=2)
        left.rowconfigure(0,weight=1);left.columnconfigure(0,weight=1);right.columnconfigure(0,weight=1);right.rowconfigure(0,weight=1)
        self.works=ttk.Treeview(left,columns=('title','year','priority'),show='headings',height=7,selectmode='browse')
        for col,width in (('title',310),('year',65),('priority',65)):
            self.works.heading(col,text=col.title());self.works.column(col,width=width)
        self.works.grid(row=0,column=0,sticky='nsew');scroll=ttk.Scrollbar(left,command=self.works.yview);scroll.grid(row=0,column=1,sticky='ns');self.works.configure(yscrollcommand=scroll.set)
        self.works.bind('<<TreeviewSelect>>',self.select_work)
        self.details=tk.Text(right,height=9,wrap='word',takefocus=True);self.details.grid(row=0,column=0,sticky='nsew')
        bar=ttk.Frame(self);bar.grid(row=3,column=0,sticky='ew',pady=6)
        self.citation=tk.StringVar();self.citations=ttk.Combobox(bar,textvariable=self.citation,state='readonly',width=28);self.citations.pack(side='left')
        ttk.Button(bar,text='Open source citation',command=self.open_source).pack(side='left',padx=6)
        self.method=tk.StringVar();self.methods=ttk.Combobox(bar,textvariable=self.method,state='readonly',width=31);self.methods.pack(side='left',padx=6)
        self.run_button=ttk.Button(bar,text='Run small reference',command=self.run);self.run_button.pack(side='left')
        self.cancel_button=ttk.Button(bar,text='Cancel',command=self.cancel,state='disabled');self.cancel_button.pack(side='left',padx=6)
        self.output=tk.Text(self,height=10,wrap='word',takefocus=True);self.output.grid(row=4,column=0,sticky='nsew')
        bottom=ttk.Frame(self);bottom.grid(row=5,column=0,sticky='ew',pady=6)
        self.object_choice=tk.StringVar();self.objects=ttk.Combobox(bottom,textvariable=self.object_choice,state='readonly',width=60);self.objects.pack(side='left')
        ttk.Button(bottom,text='Open word / counterexample in inspector',command=self.inspect).pack(side='left',padx=6)
        self.status=tk.StringVar(value='Source review, finite evidence and formal proof are shown separately.')
        ttk.Label(self,textvariable=self.status,wraplength=1050).grid(row=6,column=0,sticky='w')
        self.app.root.bind('<Escape>',lambda _: self.cancel() if self.winfo_exists() and self.winfo_ismapped() else None,add='+')
        self.bind('<Destroy>',self.destroyed,add='+')
        self.search()

    def set_text(self,widget,text):
        widget.configure(state='normal');widget.delete('1.0','end');widget.insert('1.0',text);widget.configure(state='disabled')

    def search(self):
        try:
            result=library_search(query=self.query.get(),author=self.author.get(),year=int(self.year.get()) if self.year.get() else None,priority=None if self.priority.get()=='Any' else self.priority.get())
            for item in self.works.get_children():self.works.delete(item)
            for record in result['records']:self.works.insert('', 'end',iid=record['id'],values=(record['title'],record['year'],record['priority']))
            self.status.set(f"{result['available_count']} works · {result['notice']}")
        except Exception as exc:self.status.set(f'Cannot search: {exc}')

    def select_work(self,_event=None):
        selected=self.works.selection()
        if not selected:return
        try:
            if self.job and jobs().poll(self.job)['status']=='running':self.cancel()
            self.current=work_detail(selected[0]);self.result=None;self.objects.configure(values=());self.object_choice.set('')
            self.set_text(self.details,detail_text(self.current))
            self.citations.configure(values=tuple(f"{c['review_stage']}: {c['citation_id']}" for c in self.current['citations']))
            self.citation.set(self.citations.cget('values')[0] if self.current['citations'] else '')
            titles=tuple(c['title'] for c in self.current['capabilities']);self.methods.configure(values=titles);self.method.set(titles[0] if titles else '')
            self.set_text(self.output,'Choose a reference method. Exact hypotheses, tested degrees, constructions, counterexamples and remaining obligations appear here.\n\nStatus guide:\n'+json.dumps(STATUS_HELP,indent=2))
        except Exception as exc:self.status.set(f'Cannot open work: {exc}')

    def open_source(self):
        if self.current and self.citations.current()>=0:webbrowser.open(self.current['citations'][self.citations.current()]['url'])

    def import_pack(self):
        archive=filedialog.askopenfilename(title='Import annotated research pack',filetypes=[('Research ZIP','*.zip')])
        if not archive:return
        try:
            result=import_library(archive);self.status.set('Pack '+result['status']);self.search()
        except Exception as exc:self.status.set(f'Import refused: {exc}')

    def run(self):
        try:
            if not self.current or self.methods.current()<0:raise ValueError('Select a work with an implemented reference capability.')
            method=self.current['capabilities'][self.methods.current()]['id']
            self.result=None;self.objects.configure(values=());self.object_choice.set('');self.set_text(self.output,'Running isolated reference…')
            self.job=jobs().start(method);self.run_button.configure(state='disabled');self.cancel_button.configure(state='normal')
            self.status.set('Running isolated small reference · Escape or Cancel stops the worker.')
            self.after_token=self.after(80,self.poll)
        except Exception as exc:self.status.set(f'Cannot run reference: {exc}')

    def poll(self):
        self.after_token=None
        try:
            state=jobs().poll(self.job)
            if state['status']=='running':self.after_token=self.after(80,self.poll);return
            self.run_button.configure(state='normal');self.cancel_button.configure(state='disabled')
            self.status.set(state['status'].title())
            if state['status']=='completed':
                self.result=state['result'];self.set_text(self.output,result_text(self.result))
                labels=tuple(f"{o['label']} · {o['word']} (source base {o['value_base']})" for o in self.result['inspectable_objects'])
                self.objects.configure(values=labels);self.object_choice.set(labels[0] if labels else '')
            elif state['result']:
                self.set_text(self.output,'Reference did not complete: '+state['result'].get('detail','Unknown error'))
        except Exception as exc:self.status.set(f'Reference error: {exc}')

    def cancel(self):
        if self.job:
            jobs().cancel(self.job);self.status.set('Cancelled · no proof or completed result recorded.')
        if self.after_token:self.after_cancel(self.after_token);self.after_token=None
        self.run_button.configure(state='normal');self.cancel_button.configure(state='disabled')

    def inspect(self):
        if self.result and self.objects.current()>=0:
            item=self.result['inspectable_objects'][self.objects.current()]
            translated=inspect_reference_word(item['word'],item['value_base'])
            self.app._load_witness(translated['positive_engine_word'])
            self.app.transform_help.configure(text=f"Research source {translated['source_word']} (base {translated['source_value_base']}) → positive engine {translated['positive_engine_word']}. {item['label']}")

    def destroyed(self,event):
        if event.widget is self and self.job:jobs().cancel(self.job)
