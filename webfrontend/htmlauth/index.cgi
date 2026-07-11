#!/usr/bin/perl
use strict; use warnings;
use CGI qw(:standard); use JSON::PP qw(decode_json encode_json);
use LoxBerry::System; use LoxBerry::Web;

my $cgi = CGI->new;
my $config_file = "$lbpconfigdir/pluginconfig.json";
my $status_file = "$lbpconfigdir/status.json";
my $devices_file = "$lbpconfigdir/devices.json";
my $log_file = "$lbplogdir/ble_scanner.log";
my $version = LoxBerry::System::pluginversion();
my %defaults = (enabled=>1, mqtt_topic=>'loxberry/ble_scanner', scan_window=>10, scan_pause=>2,
    offline_after=>60, minimum_rssi=>-100, publish_unknown=>1, mac_filter=>'', name_filter=>'', disabled_macs=>[]);

sub read_json { my ($file,$fallback)=@_; return $fallback unless -r $file; local $/;
    open my $fh,'<',$file or return $fallback; my $raw=<$fh>; close $fh;
    my $data=eval{decode_json($raw)}; return ref($data) eq 'HASH' ? $data : $fallback; }
sub write_json { my ($file,$data)=@_; my $tmp="$file.$$"; open my $fh,'>',$tmp or die $!;
    print {$fh} encode_json($data),"\n"; close $fh; rename $tmp,$file or die $!; }
sub esc { escapeHTML(defined $_[0] ? $_[0] : '') }
sub log_tail { return '' unless -r $log_file; open my $fh,'<',$log_file or return ''; my @l=<$fh>; close $fh;
    @l=@l[-30..-1] if @l>30; return join('',@l); }

my $cfg=read_json($config_file,{%defaults}); $cfg->{$_}=$defaults{$_} for grep {!exists $cfg->{$_}} keys %defaults;
my $devices=read_json($devices_file,{});
my @messages;
if (request_method() eq 'POST' && ($cgi->param('action')//'') eq 'save') {
    my %next=(enabled=>($cgi->param('enabled')//'') eq '1'?1:0,
              publish_unknown=>($cgi->param('publish_unknown')//'') eq '1'?1:0);
    for (qw(mqtt_topic mac_filter name_filter scan_window scan_pause offline_after minimum_rssi)) {
        $next{$_}=scalar($cgi->param($_)//''); $next{$_}=~s/^\s+|\s+$//g;
    }
    push @messages,'Topic MQTT non valido.' unless $next{mqtt_topic}=~m{\A[A-Za-z0-9._/-]{1,128}\z} && $next{mqtt_topic}!~m{\A/|/\z|//};
    push @messages,'Durata scansione: numero da 1 a 300 secondi.' unless $next{scan_window}=~m{\A\d+(?:\.\d+)?\z} && $next{scan_window}>=1 && $next{scan_window}<=300;
    push @messages,'Pausa: numero da 1 a 300 secondi.' unless $next{scan_pause}=~m{\A\d+(?:\.\d+)?\z} && $next{scan_pause}>=1 && $next{scan_pause}<=300;
    push @messages,'Timeout presenza: intero da 5 a 86400 secondi.' unless $next{offline_after}=~m{\A\d+\z} && $next{offline_after}>=5 && $next{offline_after}<=86400;
    push @messages,'RSSI minimo: intero da -127 a 0 dBm.' unless $next{minimum_rssi}=~m{\A-?\d+\z} && $next{minimum_rssi}>=-127 && $next{minimum_rssi}<=0;
    eval { qr/$next{name_filter}/i }; push @messages,'Filtro nome: espressione regolare non valida.' if $@;
    my @disabled;
    for my $mac (sort keys %{$devices}) {
        my $field='disable_'.lc($mac); $field=~s/[^a-z0-9]/_/g;
        push @disabled,uc($mac) if ($cgi->param($field)//'') eq '1';
    }
    my %known=map {uc($_)=>1} keys %{$devices};
    push @disabled,grep {!$known{uc($_)}} @{ref($cfg->{disabled_macs}) eq 'ARRAY'?$cfg->{disabled_macs}:[]};
    $next{disabled_macs}=\@disabled;
    unless (@messages) { $next{offline_after}=int($next{offline_after}); $next{minimum_rssi}=int($next{minimum_rssi});
        $next{scan_window}=0+$next{scan_window}; $next{scan_pause}=0+$next{scan_pause};
        write_json($config_file,\%next); $cfg=\%next; push @messages,'Configurazione salvata; il daemon la rilegge al prossimo ciclo.'; }
}
my $status=read_json($status_file,{running=>0,mqtt_connected=>0,message=>'Daemon non ancora avviato',devices_seen=>0,updated_at=>0});
LoxBerry::Web::lbheader("BLE Scanner MQTT V$version",'','','nojqm');
print start_form(-method=>'POST');
print q{<style>.ble-grid{display:grid;grid-template-columns:minmax(220px,320px) minmax(260px,560px);gap:.8rem 1rem;align-items:center}.ble-grid input[type=text],.ble-grid input[type=number]{width:100%;box-sizing:border-box}.ble-note{max-width:900px}.ble-msg{padding:.7rem;margin:.5rem 0;background:#e9f6ec;border-left:4px solid #2d8a4c}.ble-status{padding:1rem;max-width:900px;border-left:5px solid #b35b00;background:#fafafa}.ble-ok{border-left-color:#2d8a4c}.ble-log{max-width:900px;max-height:320px;overflow:auto;padding:.8rem;background:#17212b;color:#e5edf5;white-space:pre-wrap}.ble-table{border-collapse:collapse;max-width:900px;width:100%}.ble-table th,.ble-table td{padding:.5rem;border-bottom:1px solid #ccc;text-align:left}</style>};
print q{<h2>Bluetooth Low Energy → MQTT</h2><p class="ble-note">Cerca gli advertising BLE tramite BlueZ e pubblica presenza, RSSI, nome, UUID e dati manufacturer/service sul MQTT Gateway di LoxBerry.</p>};
print '<p class="ble-msg">',esc($_),'</p>' for @messages;
my $ok=$status->{running} && $status->{mqtt_connected}; my $updated=$status->{updated_at}?scalar(localtime($status->{updated_at})):'mai';
print '<div class="ble-status ',($ok?'ble-ok':''),'"><strong>',($ok?'ATTIVO':'ATTENZIONE'),'</strong><br>',esc($status->{message}),
      '<br>MQTT: ',($status->{mqtt_connected}?'connesso':'non connesso'),' · Dispositivi presenti: ',esc($status->{devices_seen}),'<br>Aggiornato: ',esc($updated),'</div>';
print q{<h3>Configurazione</h3><div class="ble-grid">};
my $enabled=$cfg->{enabled}?' checked':''; my $unknown=$cfg->{publish_unknown}?' checked':'';
print qq{<label for="enabled">Scanner abilitato</label><input id="enabled" name="enabled" type="checkbox" value="1"$enabled>};
for my $r ([mqtt_topic=>'Topic MQTT base'],[scan_window=>'Durata di ogni scansione (s)'],[scan_pause=>'Pausa tra scansioni (s)'],
           [offline_after=>'Assente dopo (s)'],[minimum_rssi=>'RSSI minimo (dBm)'],[mac_filter=>'MAC ammessi, separati da virgola'],[name_filter=>'Filtro nome (regex, opzionale)']) {
    print '<label for="',$r->[0],'">',$r->[1],'</label><input id="',$r->[0],'" name="',$r->[0],'" value="',esc($cfg->{$r->[0]}),'">'; }
print qq{<label for="publish_unknown">Pubblica dispositivi senza nome</label><input id="publish_unknown" name="publish_unknown" type="checkbox" value="1"$unknown>};
print q{</div><h3>Dispositivi rilevati</h3><p class="ble-note">Seleziona “Non pubblicare” per ignorare un MAC. La scelta viene applicata dal ciclo successivo e conservata negli aggiornamenti.</p>};
my %disabled=map {uc($_)=>1} @{ref($cfg->{disabled_macs}) eq 'ARRAY'?$cfg->{disabled_macs}:[]};
print q{<table class="ble-table"><thead><tr><th>Non pubblicare</th><th>Nome</th><th>MAC</th><th>RSSI</th><th>Ultimo rilevamento</th></tr></thead><tbody>};
for my $mac (sort {($devices->{$b}{last_seen}//0)<=>($devices->{$a}{last_seen}//0)} keys %{$devices}) {
    my $d=$devices->{$mac}; next unless ref($d) eq 'HASH'; my $field='disable_'.lc($mac); $field=~s/[^a-z0-9]/_/g;
    my $checked=$disabled{uc($mac)}?' checked':''; my $last=$d->{last_seen}?scalar(localtime($d->{last_seen})):'mai';
    print '<tr><td><input type="checkbox" name="',esc($field),'" value="1"',$checked,'></td><td>',esc($d->{name}//''),
          '</td><td><code>',esc($mac),'</code></td><td>',esc($d->{rssi}//''),'</td><td>',esc($last),'</td></tr>';
}
print q{</tbody></table><p><button type="submit" name="action" value="save">Salva configurazione e filtri</button></p>};
print q{<h3>Topic prodotti</h3><p class="ble-note"><code>&lt;base&gt;/availability</code>, <code>&lt;base&gt;/events</code> e, per ciascun dispositivo, <code>&lt;base&gt;/device/aa_bb_cc_dd_ee_ff/{json,rssi,presence}</code>. I topic per dispositivo sono retained.</p>};
print '<h3>Log</h3><pre class="ble-log">',esc(log_tail()),'</pre>',end_form();
LoxBerry::Web::lbfooter();
