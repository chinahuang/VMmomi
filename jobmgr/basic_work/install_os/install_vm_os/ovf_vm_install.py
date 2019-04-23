from __future__ import unicode_literals
from utils.zipUtil import unzipPackage
from utils.zipUtil import zipPackage
from utils.ipmiUtil import *
from utils.threadUtil import MultiThread
from utils.vi_server import CVmwareAdapt
from easysuite import settings
from utils.logUtil import EasysuiteLogger
from pyVmomi import vim
import shutil
import time
import re
import datetime
import os
import threading
veritas_disk_size = 200

class CInstallOvfVm(object):
    name = u'InstallOvfVm'

    def __init__(self, data):
        self.data = data
        self.vcenter_path = settings.PXE_FTP_DIR
        self.server_type = data[u'hardware'][u'server_type']
        self.vc_template_const = {}
        self.vc_template_const[u'sso_domain_name'] = u'vsphere.local'
        self.vc_template_const[u'sso_site_name'] = u'primary-site'
        self.vc_template_const[u'esxi_datastore'] = u'datastore1'
        self.vc_template_const[u'esxi_deployment_network'] = u'VMNetwork'
        self.vc_template_const[u'os_ssh_enable'] = True
        self.vc_template_const[u'appliance_deployment_option'] = u'small'
        self.vc_template_const[u'appliance_thin_disk_mode'] = True
        self.vc_template_const[u'network_mode'] = u'static'
        self.vc_template_const[u'network_ip_family'] = u'ipv4'
        self.boot_dir = settings.PXE_BOOT_DIR
        self.software_dir = settings.FTP_ROOT_DIR
        self.ftp_dir = settings.PXE_FTP_DIR
        self.clone_template_info = {}
        self.logger = self.log_handle()
        self.error_node = set()

    def execute(self):
        self.log_start()
        try:
            result = self.install()
            if result == True:
                self.log_finish()
            else:
                self.log_error(u'Install ovf failed')
                self.log_error(self.log_erro_nodes())
            return result
        except:
            self.log_error(u'Install ovf failed')
            self.log_error(self.log_erro_nodes())
            return False
        finally:
            self.find_and_del_temp_files()

    def log_erro_nodes(self):
        str = u'The nodes which show Errors or Exceptions are : '
        for node in self.error_node:
            str = str + u' ' + node

        return str

    def install(self):

        def get_thread_result_and_log(result_list, ovf_config_list, vm_common_info, task_name):
            all_result = True
            tread_cnt = 0
            for item in result_list:
                vm_input_info = self.get_vm_input_para(ovf_config_list[tread_cnt], vm_common_info)
                hostname = vm_input_info.get(u'hostname')
                ipinfo = vm_input_info.get(u'ipinfo')
                vm_name = self.get_unique_vm_name(ipinfo, hostname)
                if item == True:
                    self.logger[vm_name].info(u'Success to {} {}'.format(task_name, vm_name))
                else:
                    self.error_node.add(vm_name)
                    self.logger[vm_name].error(u'An error occured during {} {}'.format(task_name, vm_name))
                    all_result = False
                tread_cnt += 1

            if all_result == False:
                tread_cnt = 0
                for item in result_list:
                    vm_input_info = self.get_vm_input_para(ovf_config_list[tread_cnt], vm_common_info)
                    hostname = vm_input_info.get(u'hostname')
                    ipinfo = vm_input_info.get(u'ipinfo')
                    vm_name = self.get_unique_vm_name(ipinfo, hostname)
                    if item == True:
                        self.logger[vm_name].info(u'An error occured during {} other vm(s)'.format(task_name))
                        all_result = False
                    tread_cnt += 1

            return all_result

        vc_config = self.data[u'vcenter']
        esxi_config = self.data[u'esxi'][u'config']
        vm_ovf_config = self.data[u'vm_ovf_config']
        vm_common_info = self.data[u'vm_common_info']
        eth_portgroup_map = self.data[u'network'][u'eth_portgroup_map']
        self.log_info(u'Start to prepare ovf file')
        result = self.prepare_ovf_file(vm_common_info.get(u'file'))
        if result == False:
            return False
        self.log_info(u'Finish preparing ovf file')
        datastore_name_map = {}
        result = True
        for config in vm_ovf_config:
            node = self.get_node_name(config)
            try:
                real_datastore = self.get_real_datastore(vc_config, config, esxi_config, vm_common_info)
                datastore_name_map = self.get_datastore_ovf_config(real_datastore, config, datastore_name_map)
            except Exception as e:
                self.error_node.add(node)
                self.logger[node].info(e)
                result = False

        if not result:
            return False
        temp_ovf_thread = MultiThread()
        first_node_list = []
        for key, value in datastore_name_map.iteritems():
            first_node_info_config = value[0]
            first_node_list.append(first_node_info_config)
            temp_ovf_thread.add_thread(self.install_single_vm, vc_config, first_node_info_config, esxi_config, vm_common_info, mode=u'ovf')

        temp_ovf_thread.start()
        temp_ovf_thread.join()
        result_list = temp_ovf_thread.get()
        result = get_thread_result_and_log(result_list=result_list, ovf_config_list=first_node_list, vm_common_info=vm_common_info, task_name=u'deploy')
        if result == False:
            return False
        clone_thread = MultiThread()
        other_node_list = []
        for key, value in datastore_name_map.iteritems():
            if len(value) == 1:
                continue
            first_node_info = []
            first_node_info.append(value[0])
            clone_template_info = self.get_template_info(vc_config, first_node_info, vm_common_info)
            for i in range(1, len(value)):
                config = value[i]
                other_node_list.append(config)
                clone_thread.add_thread(self.install_single_vm, vc_config, config, esxi_config, vm_common_info, clone_template_info=clone_template_info, mode=u'clone')

        clone_thread.start()
        clone_thread.join()
        result_list = clone_thread.get()
        result = get_thread_result_and_log(result_list=result_list, ovf_config_list=other_node_list, vm_common_info=vm_common_info, task_name=u'clone')
        if not result:
            return False
        vm_config_thread = MultiThread()
        self.log_info(u'Start to get VM configuration template')
        vm_template_info = self.get_template_info(vc_config, vm_ovf_config, vm_common_info)
        for config in vm_ovf_config:
            vm_config_thread.add_thread(self.config_vm, vc_config, config, vm_common_info, vm_template_info, eth_portgroup_map)

        vm_config_thread.start_delay(8)
        vm_config_thread.join()
        result_list = vm_config_thread.get()
        result = get_thread_result_and_log(result_list=result_list, ovf_config_list=vm_ovf_config, vm_common_info=vm_common_info, task_name=u'config')
        if result == False:
            return False
        vc_user, vc_ip, vc_password, vm_host = self.get_vc_login_info(vc_config)
        esxi_list = []
        for config in esxi_config:
            for key, value in config.items():
                if re.match(u'plat_%s_esxi_ip_\\d{1,2}' % self.server_type, key):
                    esxi_list.append(value)
                    break

        try:
            self.config_vm_auto_start(vc_ip, vc_user, vc_password, esxi_list)
            self.log_info(u'Configuring vm auto start successfully')
        except:
            self.log_info(u'Failed to configure vm auto start')

        if os.path.exists(os.path.abspath(settings.PXE_FTP_DIR)):
            self.delete_target_subfolder(settings.PXE_FTP_DIR)
        return True

    def delete_target_subfolder(self, target_path):
        if target_path not in [settings.PXE_BOOT_DIR, settings.PXE_FTP_DIR]:
            return False
        if os.path.exists(target_path):
            try:
                for item in os.listdir(target_path):
                    path_dir = os.path.join(target_path, item)
                    if os.path.isfile(path_dir):
                        os.remove(path_dir)
                    else:
                        shutil.rmtree(path_dir)

                return True
            except Exception as e:
                return False

    def prepare_ovf_file(self, file_name):
        if file_name.endswith(u'.rar') or file_name.endswith(u'.zip'):
            file_name_noPostfix = file_name[:-4]
        elif file_name.endswith(u'.7z'):
            file_name_noPostfix = file_name[:-3]
        else:
            file_name = file_name + u'.rar'
            if not os.path.exists(os.path.join(self.software_dir, file_name)):
                file_name = file_name + u'.zip'
            file_name_noPostfix = file_name
        if os.path.exists(os.path.join(self.ftp_dir, file_name_noPostfix)):
            shutil.rmtree(os.path.join(self.boot_dir, os.path.join(self.ftp_dir, file_name_noPostfix)))
        result = unzipPackage(os.path.join(self.software_dir, file_name), os.path.join(self.ftp_dir, file_name_noPostfix))
        if result == False:
            self.log_error(u'Failed to unzip ovf Package, please check it')
            return False
        tool_dir = settings.OS_TOOL_DIR
        for item in os.listdir(tool_dir):
            path_dir = os.path.join(tool_dir, item)
            if os.path.isfile(path_dir):
                os.remove(path_dir)

        result = zipPackage(tool_dir, os.path.join(tool_dir, u'easysuite.tar'), target_format=u'tar')
        result = zipPackage(os.path.join(tool_dir, u'easysuite.tar'), os.path.join(tool_dir, u'easysuite.tar.gz'), target_format=u'gzip')
        return result

    def install_single_vm(self, vc_config, single_vm_ovf_config, esxi_config, vm_common_info, clone_template_info = u'', mode = u''):
        username, vc_ip, vc_password, vm_host = self.get_vc_login_info(vc_config)
        vc_client = CVmwareAdapt(host=vc_ip, user=username, password=vc_password)
        try:
            si = vc_client.login()
        except Exception as e:
            return False

        vm_input_info = self.get_vm_input_para(single_vm_ovf_config, vm_common_info)
        hostname = vm_input_info.get(u'hostname')
        file = vm_common_info.get(u'file')
        esxihost = vm_input_info.get(u'esxihost')
        datastore_name = vm_input_info.get(u'datastore_name')
        thin_provisioned = vm_common_info.get(u'thin_provisioned_enable')
        ipinfo = vm_input_info.get(u'ipinfo')
        ovffile, vmdkfile = self.get_ovf_file_name(file)
        cluster, datacenter, esxi_host = self.get_install_location(esxi_config, esxihost)
        vm_name = self.get_unique_vm_name(ipinfo, hostname)
        vm_obj = vc_client.get_vm(si, vm_name)
        if vm_obj is not None:
            self.logger[vm_name].info(u'A vm with the name of %s already exists, try to delete the specific vm' % vm_name)
            if format(vm_obj.runtime.powerState) == u'poweredOn':
                task = vm_obj.PowerOffVM_Task()
                vc_client.wait_for_tasks(si, [task])
            try:
                task = vm_obj.Destroy_Task()
                vc_client.wait_for_tasks(si, [task])
                self.logger[vm_name].info(u'The specific vm has been deleted'.format(vm_name))
            except:
                vm_obj = vc_client.get_vm(si, vm_name)
                if vm_obj is None:
                    self.logger[vm_name].info(u'The specific vm has been deleted'.format(vm_name))
                else:
                    self.logger[vm_name].error(u'The specific vm has not been deleted'.format(vm_name))

        try:
            if mode == u'ovf':
                self.logger[vm_name].info(u'Start to create vm {} by  importing ovf templates'.format(vm_name))
                result = vc_client.create_vm_by_ovf(si, ovffile, vmdk_path=vmdkfile, vm_name=vm_name, esxi_host=esxi_host, datastore_name=datastore_name, thin_provisioned=thin_provisioned)
            else:
                vm_name_from = clone_template_info[file][u'vm_name']
                self.logger[vm_name].info(u'Start to clone vm {}'.format(vm_name))
                result = vc_client.clone_vm_by_vm(si, vm_name_from, vm_name, False, esxi_host=esxi_host, datastore_name=datastore_name)
            return result
        except Exception as e:
            self.error_node.add(vm_name)
            if u'select datastore' in e.message:
                self.logger[vm_name].error(u'{}'.format(e))
            if u'Could not complete network copy' in e.message:
                self.logger[vm_name].error(u'Failed to clone the vm {}, the datastore volume may not be enough, please check it'.format(vm_name))
            return False

        return

    def config_vm(self, vc_config, single_vm_ovf_config, vm_common_info, clone_template_info, eth_portgroup_map = {}):
        vm_input_info = self.get_vm_input_para(single_vm_ovf_config, vm_common_info)
        hostname = vm_input_info.get(u'hostname')
        domain = vm_input_info.get(u'domain', u'default')
        node = vm_input_info.get(u'node')
        AnalyzerDB_diskCap = 0
        numCPU_expected = int(vm_input_info.get(u'numCPU'))
        time_zone = vm_input_info.get(u'time_zone')
        file = vm_common_info.get(u'file')
        passwd = vm_common_info.get(u'passwd')
        reservation_enable = vm_common_info.get(u'resource_reservation_enable')
        thin_provisioned = vm_common_info.get(u'thin_provisioned_enable')
        os_langue = vm_input_info.get(u'os_langue')
        memoryGB_expected = int(vm_input_info.get(u'memoryGB'))
        capacity_expected = int(vm_input_info.get(u'harddisk'))
        ipinfo = vm_input_info.get(u'ipinfo')
        ntp = vm_input_info.get(u'ntp')
        protection_type = vm_input_info.get(u'protection_type')
        addDisk_enable = vm_input_info.get(u'addDisk_enable')
        temp = vm_input_info.get(u'addDisk_size', 0)
        if temp is None:
            temp = 0
        addDisk_size = int(temp)
        addDisk_extend = vm_input_info.get(u'addDisk_extend')
        template_nic_number = clone_template_info[file][u'template_nic_number']
        nic_device = clone_template_info[file][u'nic_device']
        vm_name = self.get_unique_vm_name(ipinfo, hostname)
        username, vc_ip, vc_password, vm_host = self.get_vc_login_info(vc_config)
        vc_client = CVmwareAdapt(host=vc_ip, user=username, password=vc_password)
        si = vc_client.login()
        self.logger[vm_name].info(u'Start to config vm {} '.format(vm_name))
        numCPU_current = vc_client.get_numCPU(si, vm_name)
        if numCPU_expected <= numCPU_current:
            self.logger[vm_name].info(u'Expected numCPU is {}, current numCPU is {}, skip reconfiguring numCPU'.format(numCPU_expected, numCPU_current))
            numCPU_reservation = numCPU_current
        else:
            self.logger[vm_name].info(u'Expected numCPU is {}, current numCPU is {}, reconfigure numCPU'.format(numCPU_expected, numCPU_current))
            numCPU_reservation = numCPU_expected
            try:
                vc_client.reconfig_vm_cpu(si, vm_name, numCPU_expected)
            except:
                self.error_node.add(vm_name)
                self.logger[vm_name].error(u'Failed to reconfigure numCPU, task ends')
                return False

        if reservation_enable == u'Yes':
            try:
                self.logger[vm_name].info(u'Configure CPU reservation')
                vc_client.config_vm_cpu_reservation(si, vm_name, numCPU_reservation)
            except:
                self.error_node.add(vm_name)
                self.logger[vm_name].error(u'Failed to configure CPU reservation, task ends')
                return False

        memoryGB_current = vc_client.get_memoryGB(si, vm_name)
        if memoryGB_expected <= memoryGB_current:
            self.logger[vm_name].info(u'Expected memoryGB is {}GB, current memoryGB is {}GB                 , skip reconfiguring memoryGB'.format(memoryGB_expected, memoryGB_current))
            memory_reservation = memoryGB_current
        else:
            self.logger[vm_name].info(u'Expected memoryGB is {}GB, current memoryGB is {}GB             , reconfigure memoryGB'.format(memoryGB_expected, memoryGB_current))
            memory_reservation = memoryGB_expected
            try:
                vc_client.reconfig_vm_memory(si, vm_name, memoryGB_expected)
            except:
                self.error_node.add(vm_name)
                self.logger[vm_name].error(u'Failed to configure memoryGB, task ends')
                return False

        if reservation_enable == u'Yes':
            try:
                self.logger[vm_name].info(u'Configure memory reservation')
                vc_client.config_vm_memory_reservation(si, vm_name, memory_reservation)
            except:
                self.error_node.add(vm_name)
                self.logger[vm_name].error(u'Failed to configure memory reservation, task ends')
                return False

        capacity_current = vc_client.get_disksize(si, vm_name)
        uTraffic_first_disk_cap = 300
        uTraffic_disk_num = 6
        NM_Customized = (node == u'NM' or node == u'NMS') and (protection_type == u'id_protection_hot' or protection_type == u'id_protection_hot_standby' or protection_type == u'id_protection_hot_master')
        if capacity_expected < capacity_current + 1 and not NM_Customized and not addDisk_enable == u'True':
            self.logger[vm_name].info(u'Expected capacity is {}GB, current capacity is {}GB                 , skip disk expanding'.format(capacity_expected, capacity_current))
            expandValue = 0
        elif (node == u'AnalyzerDB' or node == u'Analyzer_DB') and capacity_expected > uTraffic_first_disk_cap:
            expandValue = uTraffic_first_disk_cap - capacity_current
            AnalyzerDB_diskCap = (capacity_expected - uTraffic_first_disk_cap) / uTraffic_disk_num
            self.logger[vm_name].info(u'AnalyzerDB is a customized node. The total expected capacity is {}GB, the current capacity is {}GB                     . Add a {}GB disk firstly. The remaining capacity is {}. Add {} disks with {}GB each later'.format(capacity_expected, capacity_current, uTraffic_first_disk_cap - capacity_current, capacity_expected - uTraffic_first_disk_cap, uTraffic_disk_num, AnalyzerDB_diskCap))
            try:
                vc_client.add_disk(si, vm_name, expandValue, thin_provisioned=thin_provisioned)
            except:
                self.error_node.add(vm_name)
                self.logger[vm_name].error(u'Failed to add disk, task ends')
                return False

        elif NM_Customized:
            if capacity_expected <= veritas_disk_size + capacity_current:
                self.logger[vm_name].info(u"NM's expected disk size is less than %sGB (ovf disk size and veritas disk size),resize disk size to %sGB" % (veritas_disk_size + capacity_current, veritas_disk_size + capacity_current))
                expandValue = 0
            else:
                self.logger[vm_name].info(u'NM is a customized node. Firstly, add a %sGB disk' % (capacity_expected - veritas_disk_size - capacity_current))
                try:
                    expandValue = capacity_expected - capacity_current - veritas_disk_size
                    vc_client.add_disk(si, vm_name, expandValue, thin_provisioned=thin_provisioned)
                except:
                    self.error_node.add(vm_name)
                    self.logger[vm_name].error(u'Failed to add disk, task ends')
                    return False

        elif addDisk_enable == u'True':
            if addDisk_extend == u'False':
                expandValue = max(capacity_expected - capacity_current - addDisk_size, 0)
                if expandValue == 0:
                    self.logger[vm_name].info(u"%s's expected disk size is less than %sGB(ovf disk size add extra disk size),resize disk size to %sGB" % (node, addDisk_size + capacity_current, addDisk_size + capacity_current))
            else:
                expandValue = max(capacity_expected - capacity_current, 0)
                if expandValue == 0:
                    self.logger[vm_name].info(u'Expected capacity is {}GB, the current capacity is {}GB                             , skip disk expanding'.format(capacity_expected, capacity_current))
            if not expandValue == 0:
                try:
                    vc_client.add_disk(si, vm_name, expandValue, thin_provisioned=thin_provisioned)
                except:
                    self.error_node.add(vm_name)
                    self.logger[vm_name].error(u'Failed to add disk, task ends')
                    return False

        else:
            self.logger[vm_name].info(u'Expected capacity is {}GB, the current capacity is {}GB                     , disk expanding value is {}GB '.format(capacity_expected, capacity_current, capacity_expected - capacity_current))
            try:
                expandValue = capacity_expected - capacity_current
                vc_client.add_disk(si, vm_name, expandValue, thin_provisioned=thin_provisioned)
            except:
                self.error_node.add(vm_name)
                self.logger[vm_name].error(u'Failed to add disk, task ends')
                return False

        standard_nic_num = int(vm_common_info[u'nic_num'])
        if template_nic_number < standard_nic_num:
            for i in range(standard_nic_num - template_nic_number):
                try:
                    vc_client.add_nic(si, vm_name, nic_type=nic_device)
                    self.logger[vm_name].info(u'Add a net card to {}'.format(vm_name))
                except:
                    self.error_node.add(vm_name)
                    self.logger[vm_name].error(u'Failed to add net card, task ends')
                    return False

        vc_client.modify_nic(si, vm_name, eth_portgroup_map, domain=domain)
        self.logger[vm_name].info(u'Start to power on vm')
        result = self.power_on_vm(vc_client, si, vm_name)
        if result == False:
            self.logger[vm_name].info(u'Failed to power on vm')
            return False
        else:
            self.logger[vm_name].info(u'Power on vm successfully')
            self.logger[vm_name].info(u'Try to login vm %s' % vm_name)
            result = vc_client.vm_login(si, vm_name, vm_user=u'root', vm_pwd=passwd)
            if result == False:
                self.logger[vm_name].info(u'%s login failed, please verify your OS password input' % vm_name)
                return False
            self.logger[vm_name].info(u'Start to upload script to vm')
            try:
                self.upload_script(vc_config, vc_client, si, vm_name, passwd=passwd)
                self.logger[vm_name].info(u'Upload script to vm successfully')
            except:
                self.logger[vm_name].info(u'Failed to upload script to vm')
                return False

            self.logger[vm_name].info(u'Start to configure vm')
            result = self.set_vm_config(vc_client, si, vm_name, ipinfo, hostname, time_zone, ntp, os_langue, vc_ip, expandValue, AnalyzerDB_diskCap, NM_Customized, passwd=passwd, addDisk_enable=addDisk_enable, addDisk_size=addDisk_size, standard_nic_num=standard_nic_num, thin_provisioned=thin_provisioned)
            if result == False:
                self.logger[vm_name].info(u'Failed to configure vm %s' % vm_name)
                return False
            self.logger[vm_name].info(u'Restart vm')
            result = self.power_restart_vm(vc_client, si, vm_name)
            if not result:
                self.error_node.add(vm_name)
                self.logger[vm_name].error(u'Failed to restart vm')
                return result
            self.logger[vm_name].info(u'Restart vm successfully')
            if AnalyzerDB_diskCap != 0:
                self.logger[vm_name].info(u'Start to execute addgpdisk.sh')
                self.uTraffic_add_disk(vc_client, si, vm_name, passwd=passwd)
            result = self.check_time_config(vc_client, si, vm_name, passwd=passwd)
            self.logger[vm_name].info(u'OS time compare {}'.format(self.status_bool_to_string(result)))
            self.delete_easysuite_scripts(vc_client, si, vm_name, passwd=passwd)
            self.logger[vm_name].info(u'Start to check vm connection')
            result = self.check_vm_ip(ipinfo, passwd, vc_client, si, vm_name)
            if result == True:
                self.logger[vm_name].info(u'Check vm connection: success')
                self.logger[vm_name].info(u'Finish configuring vm {}'.format(vm_name))
            else:
                self.error_node.add(vm_name)
                self.logger[vm_name].error(u'Check vm connection: failed')
                result = False
            return result

    def config_vm_auto_start(self, vc_ip, vc_user, vc_passwd, esxi_list = []):
        vc_client = CVmwareAdapt(host=vc_ip, user=vc_user, password=vc_passwd)
        si = vc_client.login()
        content = si.RetrieveContent()
        for esxi_host_ip in esxi_list:
            vm_host = vc_client.get_host(content, [vim.HostSystem], esxi_host_ip)
            if not vm_host:
                continue
            hostDefSettings = vim.host.AutoStartManager.SystemDefaults()
            hostDefSettings.enabled = True
            hostDefSettings.startDelay = 10
            order = 1
            for vhost in vm_host.vm:
                spec = vm_host.configManager.autoStartManager.config
                spec.defaults = hostDefSettings
                auto_power_info = vim.host.AutoStartManager.AutoPowerInfo()
                auto_power_info.key = vhost
                auto_power_info.startAction = u'powerOn'
                auto_power_info.startDelay = -1
                auto_power_info.startOrder = order
                auto_power_info.stopAction = u'None'
                auto_power_info.stopDelay = -1
                auto_power_info.waitForHeartbeat = u'no'
                spec.powerInfo = [auto_power_info]
                order = order + 1
                vm_host.configManager.autoStartManager.ReconfigureAutostart(spec)

        return True

    def check_time_config(self, vc_client, si, vm_name, passwd = u''):
        tool_dir = u'/opt/easysuite/maintain_tools/'
        setTime = tool_dir + u'setLocalDate.sh'
        initial_time = time.strftime(u'2018/1/2 0:0:0')
        vc_client.guest_process_manager(si, vm_name, u'root', passwd, setTime, initial_time)
        setTimeZone = tool_dir + u'setLocalTimeZone.sh'
        os_dest_file = tool_dir + u'os_property'
        result = vc_client.guest_process_manager(si, vm_name, u'root', passwd, setTimeZone, os_dest_file)
        self.logger[vm_name].info(u'Set time zone {}'.format(self.status_bool_to_string(result)))
        localtime = time.localtime()
        os_dateTime = time.strftime(u'%Y/%m/%d %H:%M:%S', localtime)
        result = vc_client.guest_process_manager(si, vm_name, u'root', passwd, setTime, os_dateTime)
        self.logger[vm_name].info(u'Set date and time {}'.format(self.status_bool_to_string(result)))
        compareTime = tool_dir + u'compare_time.sh'
        cur_time = datetime.datetime.now()
        time_str = u'"' + str(cur_time.year) + u'-' + str(cur_time.month) + u'-' + str(cur_time.day) + u' ' + str(cur_time.hour) + u':' + str(cur_time.minute) + u':' + str(cur_time.second) + u'"'
        result = vc_client.guest_process_manager(si, vm_name, u'root', passwd, compareTime, time_str)
        vc_client.guest_process_manager(si, vm_name, u'root', passwd, u'/sbin/hwclock', u'-w --utc')
        vc_client.guest_process_manager(si, vm_name, u'root', passwd, u'/usr/bin/systemctl', u'disable vmtoolsd.service')
        return result

    def delete_easysuite_scripts(self, vc_client, si, vm_name, passwd = u''):
        result = vc_client.guest_process_manager(si, vm_name, u'root', passwd, u'/bin/rm', u'/opt/easysuite.tar.gz')
        result = vc_client.guest_process_manager(si, vm_name, u'root', passwd, u'/bin/rm', u'-rf /opt/osconfig')
        result = vc_client.guest_process_manager(si, vm_name, u'root', passwd, u'/bin/rm', u'-rf /opt/easysuite')
        time.sleep(2)
        self.logger[vm_name].info(u'Delete scripts {}'.format(self.status_bool_to_string(result)))

    def uTraffic_add_disk(self, vc_client, si, vm_name, passwd):
        tool_dir = u'/opt/easysuite/maintain_tools/'
        addgpdisk = tool_dir + u'addgpdisk.sh'
        result = vc_client.guest_process_manager(si, vm_name, u'root', passwd, addgpdisk)
        self.logger[vm_name].info(u'Execute addgpdisk.sh {}'.format(self.status_bool_to_string(result)))
        time.sleep(5)

    def get_ovf_file_name(self, file):
        if file.endswith(u'.rar') or file.endswith(u'.zip'):
            vc_file_dir = file[:-4]
        elif file.endswith(u'.7z'):
            vc_file_dir = file[:-3]
        else:
            vc_file_dir = file
        filelist = os.listdir(os.path.join(self.ftp_dir, vc_file_dir))
        ovffile = u''
        vmdkfile = u''
        for file in filelist:
            if u'.ovf' in file:
                ovffile = file
            if u'.vmdk' in file:
                vmdkfile = file

        if ovffile == u'':
            return None
        else:
            return (os.path.join(self.ftp_dir, vc_file_dir, ovffile), os.path.join(self.ftp_dir, vc_file_dir, vmdkfile))
            return None

    def get_install_location(self, esxi_config, host):
        id = host
        target_config = {}
        for config in esxi_config:
            if config.has_key(u'plat_%s_esxi_id_%s' % (self.server_type, id)):
                target_config = config
                break

        datacenter = target_config.get(u'plat_%s_esxi_datacenter_%s' % (self.server_type, id))
        cluster = target_config.get(u'plat_%s_esxi_cluster_%s' % (self.server_type, id))
        ipaddress = target_config.get(u'plat_%s_esxi_ip_%s' % (self.server_type, id))
        return (cluster, datacenter, ipaddress)

    def get_harddisk(self, vm_id):
        hard_disk = {}
        for key, value in self.data.items():
            if u'groupbox_os_config.vm%s.harddisk' % str(vm_id) in key:
                lable = u'hard disk %s' % key[-1:]
                hard_disk[lable] = value

        return hard_disk

    def get_node_name(self, single_vm_ovf_config):
        vm_input_info = self.get_vm_input_para(single_vm_ovf_config, self.data[u'vm_common_info'])
        hostname = vm_input_info.get(u'hostname')
        ipinfo = vm_input_info.get(u'ipinfo')
        node = self.get_unique_vm_name(ipinfo, hostname)
        return node

    def get_vm_input_para(self, single_vm_ovf_config, vm_common_info):
        ipinfo = {}
        datastore_name = u''
        pattern = u'_eth(\\d)'
        ipinfolist = []
        real_ipinfolist = []
        numberlist = []
        for key, value in single_vm_ovf_config.items():
            if u'_eth' in key:
                result = re.findall(pattern, key)
                numberlist.append(int(result[0]))

        max_ip_number = sorted(numberlist)[-1:][0]
        for i in range(max_ip_number + 1):
            keywords = u'_eth' + str(i)
            ipinfo = {}
            for key, value in single_vm_ovf_config.items():
                if keywords in key:
                    ipinfo[key] = value

            ipinfolist.append(ipinfo)

        for ipinfo in ipinfolist:
            for key, value in ipinfo.items():
                if u'ip' in key:
                    if value is None:
                        continue
                    value = value.strip(u'\r\n')
                    if self.check_ip_valid(value):
                        real_ipinfolist.append(ipinfo)
                        break

        file = u''
        id = u''
        for key, value in single_vm_ovf_config.items():
            if re.match(u'node_vm_node_(\\d{1,3})', key):
                id = re.findall(u'node_vm_node_(\\d{1,3})', key)[0]
            if u'file' in key:
                file = value.strip()

        hostname = single_vm_ovf_config.get(u'node_vm_host_%s' % id)
        hostname = re.sub(u'[^a-zA-Z0-9]+', u'-', hostname)
        numCPU = single_vm_ovf_config.get(u'node_vm_numcpu_%s' % id)
        esxihost = single_vm_ovf_config.get(u'node_vm_blade_slot_%s' % id)
        memoryGB = single_vm_ovf_config.get(u'node_vm_memory_%s' % id)
        harddisk = single_vm_ovf_config.get(u'node_vm_harddisk_%s' % id)
        node = single_vm_ovf_config.get(u'node_vm_node_%s' % id)
        datastore_name = single_vm_ovf_config.get(u'node_vm_datastore_%s' % id)
        domain = single_vm_ovf_config.get(u'node_vm_node_domain_%s' % id, u'default')
        addDisk_enable = single_vm_ovf_config.get(u'node_vm_addDisk_enable_%s' % id)
        addDisk_size = single_vm_ovf_config.get(u'node_vm_addDisk_size_%s' % id)
        addDisk_extend = single_vm_ovf_config.get(u'node_vm_addDisk_extend_%s' % id)
        time_zone = vm_common_info[u'time_zone']
        os_langue = vm_common_info[u'langue_config']
        protection_type = vm_common_info.get(u'protection_type')
        vm_input_info = {u'node': node,
         u'hostname': hostname,
         u'numCPU': numCPU,
         u'time_zone': time_zone,
         u'file': file,
         u'os_langue': os_langue,
         u'protection_type': protection_type,
         u'esxihost': esxihost,
         u'memoryGB': memoryGB,
         u'ipinfo': real_ipinfolist,
         u'datastore_name': datastore_name,
         u'harddisk': harddisk,
         u'domain': domain,
         u'addDisk_enable': addDisk_enable,
         u'addDisk_size': addDisk_size,
         u'addDisk_extend': addDisk_extend}
        return vm_input_info

    def get_vm_ip_info(self, ipconfig):
        ip = u''
        netmask = u''
        nic = u''
        destIP = u''
        destNetmask = u''
        destGateway = u''
        for key, value in ipconfig.items():
            if self.is_in_the_key(u'_ip_', key):
                ip = value
            if self.is_in_the_key(u'_mask_', key):
                netmask = value
            if self.is_in_the_key(u'_destip_', key):
                destIP = value
            if self.is_in_the_key(u'_destmask_', key):
                destNetmask = value
            if self.is_in_the_key(u'_destgw_', key):
                destGateway = value
            if self.is_in_the_key(u'_nic_', key):
                nic = value

        ip_info_node = {u'ip': ip,
         u'nic': nic,
         u'netmask': netmask,
         u'destIP': destIP,
         u'destNetmask': destNetmask,
         u'destGateway': destGateway}
        return ip_info_node

    def is_in_the_key(self, item, key):
        match_pattern = u'^node_vm_eth\\d' + item
        match_list = re.findall(match_pattern, key)
        if len(match_list) > 0:
            return True
        else:
            return False

    def get_esxi_info_from_ip(self, esxi_config, id):
        target_config = {}
        for config in esxi_config:
            if config.has_key(u'plat_%s_esxi_id_%s' % (self.server_type, id)):
                target_config = config
                break

        ip = u''
        mask = u''
        gateway = u''
        password = u''
        for key, value in target_config.items():
            if u'_ip_' in key:
                ip = value
            if u'_mask_' in key:
                mask = value
            if u'_gw_' in key:
                gateway = value
            if u'_pwd_' in key:
                password = value

        return (ip,
         mask,
         gateway,
         password)

    def status_bool_to_string(self, status_bool):
        if status_bool == True:
            return u'success'
        if status_bool == False:
            return u'failed'

    def set_vm_config(self, vc_client, si, vm_name, ipinfo, hostname, timezone, ntp, lang, vc_ip, expandValue, AnalyzerDB_diskCap = 0, NM_Customized = False, passwd = u'', addDisk_enable = u'False', addDisk_size = 0, standard_nic_num = 6, thin_provisioned = u'No'):

        def write_ip_config(nic, ip, netmask, hostname, vm_name):
            property = []
            property.append(u'NIC_DEVICE=%s\n' % nic)
            property.append(u'IPADDR=%s\n' % ip)
            property.append(u'NETMASK=%s\n' % netmask)
            property.append(u'IP_HOSTNAME=%s\n' % hostname)
            property_path = os.path.join(settings.TEMP_DIR, u'ip_sample_{}_{}.property'.format(vm_name, nic))
            print u'property', property
            with open(property_path, u'w') as f:
                f.writelines(property)
            return property_path

        def write_route_config(nic, dest_ip, gateway, netmask, vm_name):
            property = []
            property.append(u'ACTION_TYPE=add\n')
            property.append(u'BOND_NIC=%s\n' % nic)
            property.append(u'DESTINATION_IP=%s\n' % dest_ip)
            property.append(u'GATEWAY_IP=%s\n' % gateway)
            property.append(u'NETMASK=%s\n' % netmask)
            property_path = os.path.join(settings.TEMP_DIR, u'route_sample_{}_{}.property'.format(vm_name, nic))
            with open(property_path, u'w') as f:
                f.writelines(property)
            return property_path

        def write_os_config(hostname, lang, timezone, ntp):
            property = []
            property.append(u'HOSTNAME=%s\n' % hostname)
            property.append(u'LANGUAGE=%s\n' % lang)
            property.append(u'TIME_ZONE=%s\n' % timezone)
            property.append(u'NTP_MODULE=%s\n' % ntp)
            property_path = os.path.join(settings.TEMP_DIR, u'os_sample_%s.property' % vm_name)
            with open(property_path, u'w') as f:
                f.writelines(property)
            return property_path

        tool_dir = u'/opt/easysuite/maintain_tools/'
        time.sleep(2)
        setNetwork = tool_dir + u'70-persistent-net.rules'
        result = vc_client.guest_process_manager(si, vm_name, u'root', passwd, u'/bin/cp', u'%s /etc/udev/rules.d' % setNetwork)
        self.logger[vm_name].info(u'Copy 70-persistent-net.rules to {} {}'.format(vm_name, self.status_bool_to_string(result)))
        time.sleep(10)
        eth_list = []
        for config in ipinfo:
            ip_info_node = self.get_vm_ip_info(config)
            ip = ip_info_node.get(u'ip')
            nic = ip_info_node.get(u'nic')
            netmask = ip_info_node.get(u'netmask')
            destIP = ip_info_node.get(u'destIP')
            destNetmask = ip_info_node.get(u'destNetmask')
            destGateway = ip_info_node.get(u'destGateway')
            if ip:
                property_path = write_ip_config(nic, ip, netmask, hostname, vm_name)
                dest_file = tool_dir + u'ip_%s_property' % nic
                vc_client.upload_file_to_vm(si, vm_name, u'root', passwd, property_path, dest_file, vc_ip)
                time.sleep(2)
                setip = tool_dir + u'setLocalIP.sh'
                vc_client.guest_process_manager(si, vm_name, u'root', passwd, setip, dest_file)
                time.sleep(3)
                eth_list.append(nic)
            if destGateway:
                dest_file = tool_dir + u'route_%s_property' % nic
                property_path = write_route_config(nic, destIP, destGateway, destNetmask, vm_name)
                vc_client.upload_file_to_vm(si, vm_name, u'root', passwd, property_path, dest_file, vc_ip)
                time.sleep(2)
                setroute = tool_dir + u'setLocalRoute.sh'
                vc_client.guest_process_manager(si, vm_name, u'root', passwd, setroute, dest_file)
                time.sleep(3)

        self.logger[vm_name].info(u'IP config success')
        self.logger[vm_name].info(u'Begin to turn down unused net cards')
        for eth_num in range(0, standard_nic_num):
            if u'eth%s' % eth_num in eth_list:
                continue
            result = vc_client.guest_process_manager(si, vm_name, u'root', passwd, u'/sbin/ifconfig', u'%s down' % (u'eth%s' % eth_num))
            if not result:
                self.error_node.add(vm_name)
                self.logger[vm_name].error(u'Failed to turn down the net card %s' % u'eth%s' % eth_num)
                return False
            self.logger[vm_name].info(u'Turn down net card %s sucessfully' % u'eth%s' % eth_num)

        if u')' in timezone:
            timezone = timezone.split(u')')[1]
        property_path = write_os_config(hostname, lang, timezone, ntp)
        os_dest_file = tool_dir + u'os_property'
        vc_client.upload_file_to_vm(si, vm_name, u'root', passwd, property_path, os_dest_file, vc_ip)
        time.sleep(2)
        setlang = tool_dir + u'setLocalLanguage.sh'
        sethostname = tool_dir + u'setLocalHostname.sh'
        setExpandDisk = tool_dir + u'disk_expand.sh'
        for item in [setlang, sethostname]:
            result = vc_client.guest_process_manager(si, vm_name, u'root', passwd, item, os_dest_file)
            self.logger[vm_name].info(u'{} {}'.format(item.split(u'/')[-1].split(u'.')[0], self.status_bool_to_string(result)))
            time.sleep(2)

        if expandValue != 0:
            result = vc_client.guest_process_manager(si, vm_name, u'root', passwd, setExpandDisk, str(expandValue))
            self.logger[vm_name].info(u'SetExpandDisk {}GB {}'.format(str(expandValue), self.status_bool_to_string(result)))
        else:
            time.sleep(20)
        if AnalyzerDB_diskCap and AnalyzerDB_diskCap != 0:
            uTraffic_disk_num = 6
            for i in range(0, uTraffic_disk_num):
                try:
                    vc_client.add_disk(si, vm_name, AnalyzerDB_diskCap, thin_provisioned=thin_provisioned)
                    self.logger[vm_name].info(u'AnalyzerDB adds disk {}'.format(i + 1))
                except:
                    self.error_node.add(vm_name)
                    self.logger[vm_name].error(u'Failed to add disk, task ends')
                    return False

        if NM_Customized:
            try:
                vc_client.add_disk(si, vm_name, veritas_disk_size, thin_provisioned=thin_provisioned)
                self.logger[vm_name].info(u'NM added disk successfully')
            except:
                self.error_node.add(vm_name)
                self.logger[vm_name].error(u'NM failed to add disk')
                return False

        if addDisk_enable == u'True':
            try:
                vc_client.add_disk(si, vm_name, addDisk_size, thin_provisioned=thin_provisioned)
                self.logger[vm_name].info(u'Add disk successfully')
            except:
                self.error_node.add(vm_name)
                self.logger[vm_name].error(u'Failed to add disk')
                return False

        time.sleep(30)
        return True

    def get_vm_eth_num(self, ipinfo):
        eth_list = []
        pattern = u'node_vm_eth(\\d{1,2})'
        for config in ipinfo:
            for key, value in config.items():
                eth_id = re.findall(pattern, key)
                if eth_id is not None:
                    eth_id = int(eth_id[0])
                    eth_list.append(eth_id)
                    break

        eth_max_num = max(eth_list) + 1
        return eth_max_num

    def get_unique_vm_name(self, ipinfo_list, hostname):
        north_ip = u''
        for ipinfo in ipinfo_list:
            eth_max = 7
            for eth in range(0, eth_max):
                node_num = u'node_vm_eth{}_ip_'.format(eth)
                north_ip = self.get_vm_name(node_num, ipinfo)
                if north_ip is not None and north_ip != u'':
                    vm_name = hostname + u'_' + north_ip
                    return vm_name

        vm_name = hostname + u'_' + north_ip
        return vm_name

    def get_vc_login_info(self, vc_config):
        single_vc_config = vc_config[0]
        username = single_vc_config.get(u'username')
        for key, value in single_vc_config.items():
            if u'_ip' in key:
                vc_ip = value
            if u'slot' in key:
                vm_host = value

        vc_passrod = single_vc_config[u'passwd']
        return (username,
         vc_ip,
         vc_passrod,
         vm_host)

    def get_ovf_config_as_node(self, vm_ovf_config):
        first_node_info = []
        other_node_info = []
        if len(vm_ovf_config) > 0:
            first_node_info.append(vm_ovf_config[0])
        if len(vm_ovf_config) > 1:
            for i in range(1, len(vm_ovf_config)):
                other_node_info.append(vm_ovf_config[i])

        return (first_node_info, other_node_info)

    def get_template_info(self, vc_config, vm_ovf_config, vm_common_info):
        single_vc_config = vc_config[0]
        username = single_vc_config.get(u'username')
        for key, value in single_vc_config.items():
            if u'ip' in key:
                vc_ip = value
            if u'esxihost' in key:
                vm_host = value

        vc_client = CVmwareAdapt(host=vc_ip, user=username, password=single_vc_config[u'passwd'])
        si = vc_client.login()
        clone_template_info = {}
        for single_vm_ovf_config in vm_ovf_config:
            vm_input_info = self.get_vm_input_para(single_vm_ovf_config, vm_common_info)
            hostname = vm_input_info.get(u'hostname')
            file = vm_common_info.get(u'file')
            ipinfo = vm_input_info.get(u'ipinfo')
            vm_name = self.get_unique_vm_name(ipinfo, hostname)
            file_value = {}
            file_value.update({u'vm_name': vm_name})
            file_value.update({u'template_harddisk_number': vc_client.get_hardisk_number(si, vm_name)})
            template_nic_number, nic_device = vc_client.get_nic_number(si, vm_name)
            file_value.update({u'template_nic_number': template_nic_number})
            file_value.update({u'nic_device': nic_device})
            clone_template_info.update({file: file_value})

        return clone_template_info

    def upload_script(self, vc_config, vc_client, si, vm_name, passwd = u''):
        single_vc_config = vc_config[0]
        for key, value in single_vc_config.items():
            if u'ip' in key:
                vc_ip = value
                break

        path_to_program = u'/bin/mkdir'
        dest_dir = u'/opt/easysuite'
        maintain_tool_dir = dest_dir + u'/maintain_tools'
        common_dir = dest_dir + u'/common'
        vc_client.guest_process_manager(si, vm_name, u'root', passwd, path_to_program, dest_dir)
        tool_gz_dir = os.path.join(settings.OS_TOOL_DIR, u'easysuite.tar.gz')
        vc_client.upload_file_to_vm(si, vm_name, u'root', passwd, tool_gz_dir, u'/opt/easysuite.tar.gz', vc_ip)
        time.sleep(1)
        vc_client.guest_process_manager(si, vm_name, u'root', passwd, u'/bin/tar', u'-xzvf /opt/easysuite.tar.gz -C /opt')
        time.sleep(1)
        vc_client.guest_process_manager(si, vm_name, u'root', passwd, u'/usr/bin/mv', u'-f %s %s' % (u'/opt/osconfig/*', dest_dir))
        time.sleep(1)
        vc_client.guest_process_manager(si, vm_name, u'root', passwd, u'/bin/chmod', u'+x -R %s' % dest_dir)
        time.sleep(1)
        vc_client.guest_process_manager(si, vm_name, u'root', passwd, u'/usr/bin/dos2unix', u'* %s' % maintain_tool_dir)
        time.sleep(1)
        vc_client.guest_process_manager(si, vm_name, u'root', passwd, u'/usr/bin/dos2unix', u'* %s' % common_dir)
        return True

    def power_on_vm(self, vc_client, si, vm_name):
        try:
            vc_client.power_on_vm(si, vm_name)
        except Exception as e:
            if u'Powered on' not in e.msg:
                return False

        vm = vc_client.get_vm(si, vm_name)
        starttime = datetime.datetime.now()
        while True:
            time.sleep(5)
            tools_status = vm.guest.toolsStatus
            if tools_status == u'toolsNotInstalled' or tools_status == u'toolsNotRunning':
                endtime = datetime.datetime.now()
                if (endtime - starttime).seconds > 600:
                    print u'the tools status is %s' % tools_status
                    return False
            else:
                break

    def power_restart_vm(self, vc_client, si, vm_name):
        try:
            vc_client.power_reset_vm(si, vm_name)
        except:
            return False

        time.sleep(30)
        while True:
            time.sleep(5)
            vm = vc_client.get_vm(si, vm_name)
            tools_status = vm.guest.toolsStatus
            starttime = datetime.datetime.now()
            if tools_status == u'toolsNotInstalled' or tools_status == u'toolsNotRunning':
                endtime = datetime.datetime.now()
                if (endtime - starttime).seconds > 300:
                    return False
                continue
            else:
                return True

    def check_vm_ip(self, ipinfo, passwd, vc_client, si, vm_name, timeout = 26):

        def check_connection(ipinfo, passwd = u'', stop_event = threading.Event()):
            username = u'root'
            result = False
            try_time = 0
            while try_time < timeout * 2:
                if try_time == int(timeout * 0.25):
                    self.logger[vm_name].info(u'Trying to ssh os ip for %s times, now try to ping os gateway and restart network' % int(timeout * 0.25))
                    vc_client.guest_process_manager(si, vm_name, username, passwd, u'/sbin/rcnetwork', u'restart')
                    self.logger[vm_name].info(u'The OS network has restarted')
                if try_time == int(timeout * 0.55):
                    vc_client.guest_process_manager(si, vm_name, username, passwd, u'/sbin/rcnetwork', u'restart')
                    self.logger[vm_name].info(u'The OS network has restarted again')
                for ipdict in ipinfo:
                    if stop_event.isSet():
                        return False
                    ip_info_node = self.get_vm_ip_info(ipdict)
                    if try_time == int(timeout * 0.4) or try_time == int(timeout * 0.7):
                        if ip_info_node.get(u'destGateway'):
                            try:
                                vc_client.guest_process_manager(si, vm_name, username, passwd, u'/user/bin/ping', u'%s' % ip_info_node.get(u'destGateway'))
                                self.logger[vm_name].info(u'Ping the OS gateway %s now' % ip_info_node.get(u'destGateway'))
                            except:
                                pass

                    if ip_info_node.get(u'ip'):
                        host = ip_info_node.get(u'ip')
                        try:
                            result = CsshCmd.is_connect(host, username, passwd, retry_time=1)
                        except:
                            pass

                        if result:
                            return True
                    time.sleep(5)

                try_time += 1

        stop_event = threading.Event()
        multi_thread = MultiThread()
        multi_thread.add_thread(check_connection, ipinfo, passwd, stop_event)
        multi_thread.set_daemon(True)
        multi_thread.start()
        multi_thread.join(timeout * 60)
        result = multi_thread.get()[0]
        if result == True:
            return True
        stop_event.set()

    def check_ip_valid(self, ip):
        if ip:
            value = ip.split(u'.')
            for item in value:
                if item.isdigit() == False:
                    return False

            return True
        return False

    def log_handle(self):
        logger = {}
        for single_vm_ovf_config in self.data[u'vm_ovf_config']:
            vm_input_info = self.get_vm_input_para(single_vm_ovf_config, self.data[u'vm_common_info'])
            hostname = vm_input_info.get(u'hostname')
            ipinfo = vm_input_info.get(u'ipinfo')
            node = self.get_unique_vm_name(ipinfo, hostname)
            logger[node] = EasysuiteLogger.get_logger(self.data, node)

        return logger

    def log_start(self):
        for single_vm_ovf_config in self.data[u'vm_ovf_config']:
            node = self.get_node_name(single_vm_ovf_config)
            self.logger[node].easysuite_start(u'Start to install %s' % node)

    def log_finish(self):
        for single_vm_ovf_config in self.data[u'vm_ovf_config']:
            node = self.get_node_name(single_vm_ovf_config)
            self.logger[node].easysuite_finish(u'Finish to install %s' % node)

    def log_info(self, str):
        for single_vm_ovf_config in self.data[u'vm_ovf_config']:
            node = self.get_node_name(single_vm_ovf_config)
            self.logger[node].info(str)

    def log_error(self, str):
        for single_vm_ovf_config in self.data[u'vm_ovf_config']:
            node = self.get_node_name(single_vm_ovf_config)
            self.logger[node].easysuite_error(str)

    def get_datastore_ovf_config(self, datastore_name, config, datastore_name_map):
        u"""\u5c01\u88c5\u4fe1\u606f\uff0c\u6570\u636e\u683c\u5f0f\u4e3a{\u5b58\u50a8\uff1a{{config}\uff0c{config}}}"""
        if not datastore_name_map.has_key(datastore_name):
            datastore_name_map[datastore_name] = []
        datastore_name_map[datastore_name].append(config)
        return datastore_name_map

    def get_real_datastore(self, vc_config, single_vm_ovf_config, esxi_config, vm_common_info):
        username, vc_ip, vc_password, vm_host = self.get_vc_login_info(vc_config)
        vc_client = CVmwareAdapt(host=vc_ip, user=username, password=vc_password)
        try:
            si = vc_client.login()
        except Exception as e:
            raise Exception(u'vCenter login failed')

        vm_input_info = self.get_vm_input_para(single_vm_ovf_config, vm_common_info)
        esxihost = vm_input_info.get(u'esxihost')
        datastore_name = vm_input_info.get(u'datastore_name')
        cluster, datacenter, esxi_host = self.get_install_location(esxi_config, esxihost)
        Found_data_store = False
        content = si.RetrieveContent()
        host_obj = vc_client.get_host(content, [vim.HostSystem], esxi_host)
        datastore_similar_list = []
        for store in host_obj.datastore:
            if store.name == datastore_name:
                Found_data_store = True
            elif store.info.vmfs.local == True and datastore_name in store.name and u'datastore1' in datastore_name:
                datastore_similar_list.append(store)

        if Found_data_store:
            return datastore_name
        if len(datastore_similar_list) == 1:
            return datastore_similar_list[0].name
        if len(datastore_similar_list) < 1:
            raise Exception(u"Can't find select datastore %s" % datastore_name)
        else:
            raise Exception(u'Please use accurate datastore name on this ESXi host')

    def get_vm_name(self, node_num, ipinfo):
        for key, value in ipinfo.items():
            if node_num in key:
                return value

    def find_and_del_temp_files(self):
        try:
            temp_files_path = settings.TEMP_DIR
            self.del_files(temp_files_path)
            self.log_info(u'Find and delete temp files successfully')
        except:
            self.log_info(u'Failed to find and delete temp files')

    def del_files(self, temp_files_path, topdown = True):
        for root, dirs, files in os.walk(temp_files_path, topdown):
            for name in files:
                result = re.match(u'^(route_sample_|os_sample_|ip_sample_)[a-zA-Z0-9_.\\-]*.property', name)
                if result:
                    os.remove(os.path.join(root, name))
