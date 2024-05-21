###########################################################################################################################################
##                                                                                                                                       ##
##                                        MaCoPlA - Maintenance Control and Planning Application                                         ##
##                                                                                                                                       ##
##   A CMMS application for the planning, documentation and management of machine maintenance operations by Alessandro do Carmo Silva.   ##
##                                                                                                                                       ##
###########################################################################################################################################

from os import getcwd, listdir
import sys
import json
import pandas as pd
from unidecode import unidecode
from datetime import datetime
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QTabWidget, QTableWidget, QGridLayout, QVBoxLayout, QHBoxLayout, QFormLayout,  QLabel, QScrollArea, QTableWidgetItem, QPushButton, QLineEdit, QDateEdit, QMessageBox
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QFontMetrics
from pyautogui import size as ScreenSize

app_name = 'MACOPLA - Aplicativo de Planejamento e Controle da Manutenção'
folder_path = getcwd()
script_path = folder_path[:1] + __file__[1:]
script_name = script_path.rsplit( '\\', 1 )[-1]
folder_files = tuple( file for file in listdir( folder_path ) if file != script_name )
main_db_name = 'Maintenance Database.json'
main_db_preexists = main_db_name in folder_files

for _ in range(2):
    try:
        with open( folder_path + '\\' + script_name[::-1].replace( '.py'[::-1], '.ini'[::-1], 1 )[::-1] ) as ini_file:
            for line in ini_file.read().split('\n'):
                line = line.split( '#', 1 )[0].strip()
                if not '=' in line: continue
                var, val = tuple( string.strip() for string in line.split( '=', 1 ) )
                if var == 'app_lang': app_lang = val
                if var == 'timezone': timezone = val
                del line, var, val
    except FileNotFoundError:
        with open( folder_path + '\\' + script_name[::-1].replace( '.py'[::-1], '.ini'[::-1], 1 )[::-1], 'w' ) as ini_file:
            ini_file.write( '# Language options: en-us, pt-br\napp_lang = en-us\ntimezone = sys_def' )
    else: break

if main_db_preexists:
    try:
        with open( folder_path + '\\' + main_db_name ) as data_file:
            main_db = json.loads( data_file.read() )
    except:
        load_error_app = QApplication([])
        load_error_dialog = QMessageBox()
        load_error_dialog.setWindowTitle( 'Aviso' )
        load_error_dialog.setText( 'Erro ao tentar carregar banco de dados JSON.' )
        load_error_dialog.exec()
        load_error_app.exec()
else:
    main_db = { 'machine_inv': dict() }

ScreenWidth, ScreenHeight = ScreenSize()
date_string_format = r'%d/%m/%y'
string_color_dict = {
    'bold'         : '\033[1m',
    'red'          : '\033[1;31m',
    'green'        : '\033[1;32m',
    'yellow'       : '\033[1;33m',
    'blue'         : '\033[1;34m',
    'purple'       : '\033[1;35m',
    'lightseagreen': '\033[1;36m',
    'brown'        : '\033[1;37m',
    'end'          : '\033[0m'
}
def colorize_string( string: str, color: str ) -> str:
    return f'{ string_color_dict[ color if color != 'brown' else 'white' ] }{ string }{ string_color_dict[ 'end' ] }'
status_dict = {
    'Operante'                   : 'green'        ,
    'Em Espera'                  : 'lightseagreen',
    'Parcialmente Operante'      : 'blue'         ,
    'Em Manutenção'              : 'yellow'       ,
    'Inoperante'                 : 'red'          ,
    'Desativada'                 : 'purple'       ,
    'Ausente'                    : 'brown'        ,
    'Nenhuma máquina selecionada': 'black'        ,
    ''                           : 'black'
}
default_status = tuple( status_dict.keys() )[0]
default_manufacturer = 'Desconhecido'
default_model = 'Desconhecido'
default_supplier = 'Desconhecido'
default_sector = 'Não se aplica'
default_id = 'Não consta'
default_acquisition_date = 'Desconhecida'
excluded_manufacturers = { default_manufacturer, 'Nenhum', '' }
excluded_suppliers = { default_supplier, 'Nenhum', '' }
excluded_models = { default_model, 'Nenhum', '' }
excluded_sectors = { default_sector, 'Outros', 'Nenhum', '' }
attribute_labels = ( 'Tipo', 'Fabricante', 'Modelo', 'Fornecedor', 'Setor', 'N° de Patrimônio', 'Data de Aquisição', 'Status' )
attribute_internal_names = ( 'type', 'manufacturer', 'model', 'supplier', 'sector', 'id', 'acquisition_date', 'status' )

class Machine:
    procedures_array = tuple()
    procedures_schedule = list()
    procedures_history = list()
    spec_sheet = pd.DataFrame()
    features_sheet = pd.DataFrame()
    def __init__( self, type: str, manufacturer: str = default_manufacturer, model: str = default_model, supplier: str = default_supplier, sector: str = default_sector, id: int | float | str = default_id, acquisition_date: datetime | str = default_acquisition_date, status: str = default_status ) -> None:
        self.type, self.manufacturer, self.model, self.supplier, self.sector, self.id, self.acquisition_date = type, manufacturer, model, supplier, sector, id, acquisition_date
        if status in set( status_dict.keys() ) | { 'Nenhuma máquina selecionada' }: self.status = status
        else: raise Exception( f'{ status } status isn\'t on the status dictionary.' )
    def GetName( self, shorthand: bool = False ) -> str:
        machine_name = f'{ self.type }{ ( ' ' + self.manufacturer ) if self.manufacturer not in excluded_manufacturers else '' }{ ( ' ' + self.model ) if self.model not in excluded_models else '' }{ ( ' – ' + self.sector ) if ( self.sector not in excluded_sectors ) and not ( self.manufacturer not in excluded_manufacturers and self.model not in excluded_models ) and not shorthand else '' }{ ( ' – ID: ' + self.id ) if self.id in { int, float } and not self.IsUnique() and not shorthand else '' }'
        return machine_name
    def GetInfoBoxWidget( self ) -> QWidget:
        attribute_values = tuple( str( getattr( self, internal_name ) ) for internal_name in attribute_internal_names )
        info_box = QWidget()
        info_box_layout = QGridLayout()
        info_box_layout.setSpacing( 0 )
        info_box_font = QFont( ( 'Times', ), 12, 1 )
        info_box_font_width = QFontMetrics( info_box_font ).averageCharWidth()
        field_width = min( 150, round( ScreenWidth * 0.125 ), round( ( len( max( attribute_labels, key = len ) ) + 1 ) * info_box_font_width * 1.25 ) + 10 )
        value_width = min( 650, round( ScreenWidth * 0.465 ), round(   len( max( attribute_values, key = len ) )       * info_box_font_width * 1.25 ) + 10 )
        for idx, field, value in zip( range( len( attribute_labels ) ), attribute_labels, attribute_values ):
            field_widget = QLabel( field + ':' )
            value_widget = QLabel( value if type( value ) == str else str( value ) )
            value_widget.setAlignment( Qt.AlignmentFlag.AlignRight )
            field_widget.setFont( info_box_font )
            value_widget.setFont( info_box_font )
            field_widget.setStyleSheet( '* { border: 2px inset dimgray; background-color: aliceblue; }' )
            value_widget.setStyleSheet( '* { border: 2px inset dimgray; background-color: aliceblue; }' )
            if field == attribute_labels[7]: value_widget.setStyleSheet( '* { ' + f'border: 2px inset dimgray; color: { status_dict[ value ] }; background-color: aliceblue;{ ' font-weight: bold;' if not status_dict[ value ] == 'black' else '' }' + ' }' )
            field_widget.setFixedWidth( field_width )
            value_widget.setFixedWidth( value_width )
            info_box_layout.addWidget( field_widget, idx, 0, 1, 1, alignment = Qt.AlignmentFlag.AlignLeft  )
            info_box_layout.addWidget( value_widget, idx, 1, 1, 1, alignment = Qt.AlignmentFlag.AlignRight )
        info_box.setLayout( info_box_layout )
        return info_box
    def GetSpecSheetWidget( self ) -> QTableWidget | None:
        sheet_widget = QTableWidget()
        if not ( self.spec_sheet.empty and self.features_sheet.empty ):
            sheet_widget.setRowCount( len( self.spec_sheet ) + len( self.features_sheet ) )
            sheet_widget.setColumnCount( max( len( self.spec_sheet.columns ), len( self.features_sheet.columns ) ) )
            sheet_widget.verticalHeader().setVisible( False )
            sheet_widget.horizontalHeader().setVisible( False )
            font_family = ( 'Times', )
            font_size = 10
            sheet_font = QFont( font_family, font_size )
            sheet_header_font = QFont( font_family, round( font_size * 1.25 ), 2 )
            font_width = QFontMetrics( sheet_font ).averageCharWidth()
            sheet_widget.setFont( sheet_font )
            max_col_width = max( 300, round( ScreenWidth * 0.15 ) )
            for col_idx in range( len( self.spec_sheet.columns ) ):
                for row_idx in range( len( self.spec_sheet ) ):
                    sheet_widget.setColumnWidth( col_idx, min( max_col_width, max( sheet_widget.columnWidth( col_idx ), len( self.spec_sheet.iloc[ row_idx, col_idx ] ) * font_width + 10 ) ) )
                    sheet_widget.setItem( row_idx, col_idx, QTableWidgetItem( str( self.spec_sheet.iloc[ row_idx, col_idx ] ) ) )
            for row_idx in range( len( self.spec_sheet ), len( self.spec_sheet ) + len( self.features_sheet ) ):
                for col_idx in range( len( self.features_sheet.columns ) ):
                    sheet_widget.setColumnWidth( col_idx, min( max_col_width, max( sheet_widget.columnWidth( col_idx ), len( self.features_sheet.iloc[ row_idx - len( self.spec_sheet ), col_idx ] ) * font_width + 10 ) ) )
                    sheet_widget.setItem( row_idx, col_idx, QTableWidgetItem( str( self.features_sheet.iloc[ row_idx - len( self.spec_sheet ), col_idx ] ) ) )
                if 0 < len( self.features_sheet.columns ) <= 3 and not any( self.features_sheet.iloc[ :, 1:: ].any( axis = 0 ) ):
                    sheet_widget.setSpan( row_idx, 0, 1, sheet_widget.columnCount() )
                    if row_idx > len( self.features_sheet ):
                        row_item = sheet_widget.item( row_idx, 0 )
                        row_item.setTextAlignment( Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter )
            table_width = sum( sheet_widget.columnWidth( col ) for col in range( sheet_widget.columnCount() ) )
            if not self.spec_sheet.empty:
                sheet_widget.setSpan( 0, 0, 1, sheet_widget.columnCount() )
                spec_sheet_header = QTableWidgetItem( str( self.spec_sheet.iloc[ 0, 0 ] ) )
                spec_sheet_header.setTextAlignment( Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter )
                spec_sheet_header.setFont( sheet_header_font )
                sheet_widget.setItem( 0, 0, spec_sheet_header )
            if not self.features_sheet.empty:
                features_sheet_header = QTableWidgetItem( str( self.features_sheet.iloc[ 0, 0 ] ) )
                features_sheet_header.setTextAlignment( Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter )
                features_sheet_header.setFont( sheet_header_font )
                sheet_widget.setItem( len( self.spec_sheet ), 0, features_sheet_header )
            sheet_widget.setMinimumWidth( max( 60, table_width + 19 ) )
            return sheet_widget
        else: return None
    def IsUnique( self ) -> bool: # Work in Progress!
        unique_status = True
        return unique_status

null_machine = Machine( 'Nenhuma máquina selecionada', 'Nenhuma máquina selecionada', 'Nenhuma máquina selecionada', 'Nenhuma máquina selecionada', 'Nenhuma máquina selecionada', 'Nenhuma máquina selecionada', 'Nenhuma máquina selecionada', 'Nenhuma máquina selecionada' )
null_machine.spec_sheet = pd.DataFrame( {
    'A': ( 'Especificações Técnicas', 'Specification', 'Maximum Force', 'Return Force', 'Rapid Descent Speed', 'Working Speed - Slow', 'Useful Working Length', 'Return Speed', 'Distance between Table and Piston', 'Machine Weight', 'Number of Cylinders', 'General Aspects', 'Positioning Precision on X-axis', 'Machine Axes' ),
    'B': ( '', 'Value', '450', '28', '0/100', '0/10', '2100', '0/120', '340', '3500', '2', 'Delem Control', 'With NR12', '4 (y1, y2, x, r)' ),
    'C': ( '', 'Unit', 'KN', 'KN', 'MM/S', 'MM/S', 'MM', 'MM/S', 'MM', 'KG', 'QUANT', '-', '-', '-' )
} ) # PLACEHOLDER!
null_machine.features_sheet = pd.DataFrame( {
    'A': ( 'Características Gerais', 'Peso = 500kg', 'Número de partes = 2000' ),
    'B': ( '', '', '' ),
    'C': ( '', '', '' )
} ) # PLACEHOLDER!

class WorkOrdersSheet: # WORK IN PROGRESS!
    def __init__( self, WO_Sheet: pd.DataFrame = pd.DataFrame() ) -> None:
        self.WO_Sheet = WO_Sheet
    def GetWidget( self ) -> QWidget:
        widget = QWidget()
        layout = QGridLayout()
        scroll_area = QScrollArea()
        scroll_area.setAlignment( Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom )
        scroll_area.setWidget( self.GetSheet() )
        layout.addWidget( scroll_area, 1, 0, -1, -1, alignment = Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom )
        widget.setLayout( layout )
        return widget
    def GetSheet( self ) -> QTableWidget:
        sheet_widget = QTableWidget()
        sheet_widget.setRowCount( len( self.WO_Sheet ) )
        sheet_widget.setColumnCount( len( self.WO_Sheet ) )
        sheet_widget.verticalHeader().setVisible( False )
        sheet_widget.horizontalHeader().setVisible( False )
        font_family = ( 'Times', )
        font_size = 10
        sheet_font = QFont( font_family, font_size )
        sheet_header_font = QFont( font_family, round( font_size * 1.25 ), 2 )
        font_width = QFontMetrics( sheet_font ).averageCharWidth()
        sheet_widget.setFont( sheet_font )
        for col_idx in range( len( self.WO_Sheet.columns ) ):
            max_col_width = max( 300, round( ScreenWidth * 0.15 ) ) # SHOULD BE COLUMN SENSITIVE! MAKE SURE TO PROPERLY IMPLEMENT LOGIC!
            for row_idx in range( len( self.WO_Sheet ) ):
                cel_text = self.WO_Sheet.iloc[ row_idx, col_idx ]
                sheet_widget.setColumnWidth( col_idx, min( max_col_width, max( sheet_widget.columnWidth( col_idx ), len( cel_text ) * font_width + 10 ) ) )
                sheet_widget.setItem( row_idx, col_idx, QTableWidgetItem( str( self.WO_Sheet.iloc[ row_idx, col_idx ] ) ) )
        table_width = sum( sheet_widget.columnWidth( col ) for col in range( sheet_widget.columnCount() ) )
        if not self.WO_Sheet.empty:
            sheet_widget.setSpan( 0, 0, 1, sheet_widget.columnCount() )
            WO_Sheet_header = QTableWidgetItem( str( self.WO_Sheet.iloc[ 0, 0 ] ) )
            WO_Sheet_header.setTextAlignment( Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter )
            WO_Sheet_header.setFont( sheet_header_font )
            sheet_widget.setItem( 0, 0, WO_Sheet_header )
        sheet_widget.setMinimumWidth( max( 60, table_width + 19 ) )
        return sheet_widget

placeholder_sheet = {
    'Work Order': ['WO001', 'WO002', 'WO003', 'WO004', 'WO005'],
    'Description': ['Repair Laptop', 'Install Software', 'Replace Hard Drive', 'Upgrade RAM', 'Virus Removal'],
    'Status': ['Completed', 'In Progress', 'Pending', 'Completed', 'In Progress']
} # PLACEHOLDER
null_work_sheet = WorkOrdersSheet( pd.DataFrame( placeholder_sheet ) ) # PLACEHOLDER

class MainWindow( QWidget ):
    def __init__( self ) -> None:
        super().__init__()
        self.setWindowTitle( app_name )
        self.main_layout = QGridLayout( self )
        self.setLayout( self.main_layout )
        self.setGeometry( round( ScreenWidth * 0.1 ), round( ScreenHeight * 0.1 ), round( ScreenWidth * 0.8 ), round( ScreenHeight * 0.8 ) )
        self.tab = QTabWidget( self )
        
        # Maintenance Calendar
        self.cal_tab = QWidget( self )
        self.cal_tab_layout = QVBoxLayout()
        self.cal_tab.setLayout( self.cal_tab_layout )
        self.tab.addTab( self.cal_tab, 'Calendário de Manutenções Preventivas' )
        
        # Preventive Maintenance Documentation
        self.doc_tab = QWidget( self )
        self.doc_tab_layout = QVBoxLayout()
        self.doc_tab.setLayout( self.doc_tab_layout )
        self.tab.addTab( self.doc_tab, 'Controle de Manutenções Preventivas' )
        
        # Repair Registry
        self.his_tab = QWidget( self )
        self.his_tab_layout = QVBoxLayout()
        self.worksheet = null_work_sheet.GetSheet()
        self.his_tab_layout.addWidget( self.worksheet )
        self.his_tab.setLayout( self.his_tab_layout )
        self.tab.addTab( self.his_tab, 'Registro de Ordens de Serviço' )
        
        # Machine Inventory
        self.inv_tab = QWidget( self )
        self.inv_tab_layout = QGridLayout()
        self.inv_tab.setLayout( self.inv_tab_layout )
        self.inv_tab_search_bar = QLineEdit()
        self.inv_tab_search_bar.setPlaceholderText( 'Buscar Máquina...' )
        self.inv_tab_search_bar.setFixedWidth( min( 450, round( ScreenWidth * 0.4 ) ) + 37 )
        self.inv_tab_layout.addWidget( self.inv_tab_search_bar, 0, 0, 1, 1, alignment = Qt.AlignmentFlag.AlignLeft )
        self.inv_tab_scroll_area = QScrollArea()
        self.inv_tab_scroll_area.setFixedWidth( min( 450, round( ScreenWidth * 0.4 ) ) + 37 )
        self.inv_tab_scroll_widget = QWidget()
        self.inv_tab_scroll_layout = QVBoxLayout()
        self.inv_tab_scroll_layout.setSpacing( 0 )
        self.update_inv_tab_scroll_list()
        self.inv_tab_scroll_widget.setLayout( self.inv_tab_scroll_layout )
        self.inv_tab_scroll_area.setWidget( self.inv_tab_scroll_widget )
        self.inv_tab_layout.addWidget( self.inv_tab_scroll_area, 1, 0, -1, 1, alignment = Qt.AlignmentFlag.AlignLeft )
        self.inv_tab_add_machine = QPushButton( 'Adicionar Máquina' )
        #self.inv_tab_add_machine.clicked.connect(  )
        self.inv_tab_layout.addWidget( self.inv_tab_add_machine, 0, 1, 1, 1 )
        self.inv_tab_remove_machine = QPushButton( 'Remover Máquina' )
        self.inv_tab_remove_machine.setEnabled( False )
        #self.inv_tab_remove_machine.clicked.connect(  )
        self.inv_tab_layout.addWidget( self.inv_tab_remove_machine, 0, 2, 1, 1 )
        self.inv_tab_edit_machine = QPushButton( 'Editar Máquina' )
        self.inv_tab_edit_machine.setEnabled( False )
        #self.inv_tab_edit_machine.clicked.connect(  )
        self.inv_tab_layout.addWidget( self.inv_tab_edit_machine, 1, 1, 1, 1, alignment = Qt.AlignmentFlag.AlignTop )
        self.inv_tab_machine_history = QPushButton( 'Histórico de Manutenções' )
        self.inv_tab_machine_history.setEnabled( False )
        #self.inv_tab_machine_history.clicked.connect(  )
        self.inv_tab_layout.addWidget( self.inv_tab_machine_history, 1, 2, 1, 1, alignment = Qt.AlignmentFlag.AlignTop )
        self.inv_tab_info_display_scroll = QScrollArea()
        self.inv_tab_info_display_scroll.setMinimumHeight( min( 300, round( ScreenHeight * 0.35 ) ) )
        self.inv_tab_info_display = QWidget()
        self.inv_tab_info_display_layout = QVBoxLayout()
        self.inv_tab_info_display_layout.setSpacing( 0 )
        self.inv_tab_info_display_top_box = null_machine.GetInfoBoxWidget()
        self.inv_tab_info_display_layout.addWidget( self.inv_tab_info_display_top_box, alignment = Qt.AlignmentFlag.AlignHCenter )
        self.inv_tab_info_display_spec_sheet = null_machine.GetSpecSheetWidget()
        if self.inv_tab_info_display_spec_sheet: self.inv_tab_info_display_layout.addWidget( self.inv_tab_info_display_spec_sheet, alignment = Qt.AlignmentFlag.AlignHCenter )
        self.inv_tab_info_display.setLayout( self.inv_tab_info_display_layout )
        self.inv_tab_info_display_scroll.setWidget( self.inv_tab_info_display )
        self.inv_tab_layout.addWidget( self.inv_tab_info_display_scroll, 2, 1, -1, 2 )
        self.tab.addTab( self.inv_tab, 'Inventário de Máquinas' )
        self.main_layout.addWidget( self.tab, 0, 0, 1, 1 )
        
        self.save_buttom = QPushButton( 'Salvar Alterações' )
        self.save_buttom.setEnabled( False )
        self.save_buttom.clicked.connect( self.SaveChangesClick )
        self.main_layout.addWidget( self.save_buttom, 2, 0, alignment = Qt.AlignmentFlag.AlignBottom )
    
    def update_inv_tab_scroll_list( self, search_filter_text: str = '' ) -> None:
        while self.inv_tab_scroll_layout.count():
            machine_button = self.inv_tab_scroll_layout.takeAt(0).widget()
            if machine_button: machine_button.deleteLater()
            del machine_button
        for registred_machine in range( 101 ):
            if search_filter_text and not ( ( search_filter_text in unidecode( registred_machine.GetName() ).replace( '– ', '' ).replace( '-','' ).upper() ) or ( search_filter_text.isnumeric() and type( registred_machine.id ) in { int, float } and float( search_filter_text ) == registred_machine.id ) ): continue
            machine_button = QPushButton( f'Item { registred_machine }' )
            machine_button.setFixedSize( QSize( min( 450, round( ScreenWidth * 0.4 ) ), 15 ) )
            machine_button.setStyleSheet( 'QPushButton { font-family: Arial; font-size: 7pt; }' )
            self.inv_tab_scroll_layout.addWidget( machine_button )
            del machine_button
    
    #search_filter_text = unidecode( search_filter_text.replace( '–', '' ) ).replace( '-','' ).replace( '  ', ' ' ).upper()

    def WarningMessage( self, dialog_box_message: str, dialog_box_title: str = 'Erro' ) -> None:
        self.dialog_box = QMessageBox( self )
        self.dialog_box.setWindowTitle( dialog_box_title )
        self.dialog_box.setText( dialog_box_message )
        self.dialog_box.exec()
    
    def SaveChangesClick( self ) -> None:
        try: SaveChanges()
        except: self.WarningMessage( 'Falha ao salvar as alterações.' )
        else: self.save_buttom.setEnabled( False )

def SaveChanges() -> None:
    with open( folder_path + '\\' + main_db_name, 'w' ) as data_file:
        data_file.write( json.dumps( main_db ) )

app = QApplication( sys.argv )
window = MainWindow()
window.show()
app.exec()