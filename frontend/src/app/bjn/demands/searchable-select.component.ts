/**
 * Lista pesquisável reutilizada pelos cadastros corporativos do BJN.
 *
 * A escolha é explícita para departamentos (catálogo obrigatório). Para agências,
 * a digitação livre permanece disponível enquanto o catálogo ainda está incompleto.
 * O componente não consulta a rede: recebe somente os valores devolvidos pela API.
 */
import {CommonModule} from '@angular/common';
import {Component, ElementRef, EventEmitter, HostListener, Input, OnChanges, Output, SimpleChanges, ViewChild, inject} from '@angular/core';

/** Retira diferenças de caixa e acentuação para permitir busca por código ou nome. */
export function normalizeDirectorySearch(text:string):string {
  return text.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLocaleLowerCase('pt-BR').trim();
}

@Component({
  selector:'app-bjn-searchable-select',
  standalone:true,
  imports:[CommonModule],
  template:`
    <div class="bjn-combobox" [class.bjn-combobox--open]="isOpen">
      <div class="bjn-combobox-field">
        <input #searchInput class="bjn-combobox-input" type="text"
          [id]="inputId" [value]="inputText" [placeholder]="placeholder" [disabled]="disabled"
          [attr.maxlength]="maxLength" [attr.aria-label]="ariaLabel || null"
          role="combobox" aria-autocomplete="list" aria-haspopup="listbox"
          [attr.aria-controls]="inputId+'-options'" [attr.aria-expanded]="isOpen"
          [attr.aria-required]="required" [attr.aria-activedescendant]="isOpen && activeIndex>=0 && matches.length?optionId(activeIndex):null"
          autocomplete="off" (focus)="openMenu()" (input)="onInput($event)"
          (keydown)="onKeydown($event)" />
        <button type="button" class="bjn-combobox-toggle" [disabled]="disabled"
          [attr.aria-label]="isOpen?'Fechar opções':'Abrir opções'" [attr.aria-expanded]="isOpen"
          (click)="toggleMenu()"><span aria-hidden="true">⌄</span></button>
      </div>
      @if(isOpen){
        <div class="bjn-combobox-popover" [id]="inputId+'-options'" role="listbox"
          [attr.aria-label]="ariaLabel || 'Opções disponíveis'">
          @for(option of matches;track option;let index=$index){
            <div class="bjn-combobox-option" role="option" [id]="optionId(index)"
              [attr.aria-selected]="option===value" [class.active]="index===activeIndex"
              (pointerdown)="selectOption(option);$event.preventDefault()" (click)="selectOption(option)">{{option}}</div>
          } @empty {
            <div class="bjn-combobox-empty" role="status">{{options.length?'Nenhum resultado. Refine sua busca.':allowCustomValue?'Nenhuma opção cadastrada. Digite o valor desejado.':'Nenhum registro disponível no cadastro.'}}</div>
          }
          @if(hasMoreOptions){<p class="bjn-combobox-more">Exibindo as primeiras {{maxVisibleOptions}} opções. Digite para refinar a lista.</p>}
        </div>
      }
    </div>`
})
export class BjnSearchableSelectComponent implements OnChanges {
  private readonly host=inject(ElementRef<HTMLElement>);
  @ViewChild('searchInput') private searchInput?:ElementRef<HTMLInputElement>;
  @Input({required:true}) inputId='';
  @Input() options:readonly string[]=[];
  @Input() value='';
  @Input() placeholder='Digite um código ou nome';
  @Input() ariaLabel='';
  @Input() required=false;
  @Input() disabled=false;
  @Input() allowCustomValue=false;
  @Input() maxLength=120;
  @Output() readonly valueChange=new EventEmitter<string>();

  readonly maxVisibleOptions=40;
  inputText='';
  isOpen=false;
  activeIndex=-1;
  private searchTerm='';
  private cachedOptions:readonly string[]|null=null;
  private cachedSearchTerm='';
  private cachedMatches:string[]=[];
  private cachedTotal=0;

  /** Atualiza a apresentação quando uma escolha vem de fora (ex.: limpar filtros). */
  ngOnChanges(changes:SimpleChanges):void {
    if(changes['value'] && !this.isOpen){this.inputText=this.value||'';}
  }

  /** Limita a quantidade de linhas renderizadas, mesmo em catálogos grandes. */
  get matches():string[]{
    if(this.cachedOptions!==this.options || this.cachedSearchTerm!==this.searchTerm){
      const term=normalizeDirectorySearch(this.searchTerm);
      const all=term?this.options.filter(option=>normalizeDirectorySearch(option).includes(term)):[...this.options];
      this.cachedTotal=all.length;
      this.cachedMatches=all.slice(0,this.maxVisibleOptions);
      this.cachedOptions=this.options;this.cachedSearchTerm=this.searchTerm;
    }
    return this.cachedMatches;
  }
  get hasMoreOptions():boolean {void this.matches;return this.cachedTotal>this.maxVisibleOptions;}
  optionId(index:number):string{return `${this.inputId}-option-${index}`;}

  /** Ao abrir após uma seleção, mostra todas as opções em vez de apenas a já escolhida. */
  openMenu():void {
    if(this.disabled)return;
    if(!this.isOpen){this.searchTerm=this.inputText===this.value?'':this.inputText;}
    this.isOpen=true;
    this.activeIndex=this.matches.length?0:-1;
  }
  toggleMenu():void {
    if(this.isOpen){this.closeMenu();return;}
    this.openMenu();this.searchInput?.nativeElement.focus();
  }
  onInput(event:Event):void {
    const entered=(event.target as HTMLInputElement).value;
    this.inputText=entered;this.searchTerm=entered;this.isOpen=true;
    this.activeIndex=this.matches.length?0:-1;
    // Campos de departamento exigem escolha no cadastro; filtros e agências aceitam texto parcial.
    this.valueChange.emit(this.allowCustomValue?entered:'');
  }
  /** Retém somente opções existentes quando a unidade deve pertencer ao CSV. */
  selectOption(option:string):void {
    this.inputText=option;this.valueChange.emit(option);
    this.isOpen=false;this.searchTerm='';this.activeIndex=-1;
  }
  onKeydown(event:KeyboardEvent):void {
    if(event.key==='ArrowDown' || event.key==='ArrowUp'){
      event.preventDefault();
      if(!this.isOpen){this.openMenu();return;}
      const count=this.matches.length;
      if(count)this.activeIndex=(this.activeIndex+(event.key==='ArrowDown'?1:-1)+count)%count;
    }else if(event.key==='Enter' && this.isOpen){
      event.preventDefault();
      if(this.activeIndex>=0 && this.matches[this.activeIndex])this.selectOption(this.matches[this.activeIndex]);
      else this.closeMenu();
    }else if(event.key==='Escape' && this.isOpen){
      event.preventDefault();this.closeMenu();
    }else if(event.key==='Tab'){
      this.closeMenu();
    }
  }
  /** Fecha sem aceitar códigos ou nomes parciais para departamentos. */
  private closeMenu():void {
    if(!this.allowCustomValue){
      const exact=this.options.find(option=>normalizeDirectorySearch(option)===normalizeDirectorySearch(this.inputText));
      if(exact && exact!==this.value)this.valueChange.emit(exact);
      this.inputText=exact||this.value||'';
    }
    this.isOpen=false;this.searchTerm='';this.activeIndex=-1;
  }
  @HostListener('focusout',['$event'])
  onFocusOut(event:FocusEvent):void {
    if(event.relatedTarget instanceof Node && this.host.nativeElement.contains(event.relatedTarget))return;
    this.closeMenu();
  }
  @HostListener('document:pointerdown',['$event'])
  onDocumentPointerDown(event:PointerEvent):void {
    if(event.target instanceof Node && !this.host.nativeElement.contains(event.target))this.closeMenu();
  }
}
