module LSF
  module Helpers

    include Chef::Mixin::ShellOut

    def get_hostname(ip_address)
      Chef::Resource::RubyBlock.send(:include, Chef::Mixin::ShellOut)      
      command = "getent hosts #{ip_address} | awk '{ print $NF }'"
      command_out = shell_out(command)
      return command_out.stdout.strip
    end
  end
end

Chef::Recipe.include(LSF::Helpers)
Chef::Resource::Template.include(LSF::Helpers)