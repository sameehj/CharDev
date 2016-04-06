/* vigenere_module.c: Example char device module.
 *
 */
/* Kernel Programming */
#define MODULE
#define LINUX
#define __KERNEL__

#include <linux/kernel.h> 
#include <linux/module.h> 	
#include <linux/fs.h>       		
#include <asm/uaccess.h>
#include <linux/errno.h>  
#include <linux/sched.h> 
#include <linux/slab.h>

#include "my_module.h"

#define VIGENERE_DEVICE "my_device"
#define BUFFER_SIZE 4096
#define MAX_DEVICES 256

//Enable the define to start debug printing
//#define DEBUG

#ifdef DEBUG
#define _DBG(fmt, args...) printk(KERN_DEBUG "%s: " fmt "\n", __FUNCTION__, ##args)
#else
# define _DBG(fmt, args...) do { } while(0);
#endif

MODULE_LICENSE("GPL");
MODULE_AUTHOR("Sameeh Jubran");

/* globals */
int my_major = 0; /* will hold the major # of my device driver */
char* buffers[MAX_DEVICES + 1];
int read_index[MAX_DEVICES + 1];
int write_index[MAX_DEVICES + 1];

struct file_operations my_fops = {
	.open = my_open,
	.release = my_release,
	.read = my_read,
	.write = my_write,
	.ioctl = my_ioctl
};


int init_module(void)
{
	_DBG();
	if( my_major > 0 )
	{

	}

	my_major = register_chrdev(my_major, VIGENERE_DEVICE, &my_fops);

	if (my_major < 0)
	{
		return my_major;
	}
	int i = 0;
	for(i = 0 ; i < MAX_DEVICES ; i++)
	{
		buffers[i] = NULL;
		read_index[i] = 0;
		write_index[i] = 0;
	}
	return 0;
}


void cleanup_module(void)
{
	_DBG();
	unregister_chrdev(my_major, VIGENERE_DEVICE);
	int i = 0;
	for(i = 0 ; i < MAX_DEVICES ; i++)
	{
		if(!buffers[i])
			kfree(buffers[i]);
	}

	return;
}


int my_open(struct inode *inode, struct file *filp)
{
	_DBG();
	if (filp->f_mode & FMODE_READ)
	{
		//
		// handle read opening
		//
	}

	if (filp->f_mode & FMODE_WRITE)
	{
		//
		// handle write opening
		//
	}
	return 0;
}


int my_release(struct inode *inode, struct file *filp)
{
	_DBG();
	if (filp->f_mode & FMODE_READ)
	{
		//
		// handle read closing
		// 
	}

	if (filp->f_mode & FMODE_WRITE)
	{
		//
		// handle write closing
		//
	}

	return 0;
}


ssize_t my_read(struct file *filp, char *buf, size_t count, loff_t *f_pos)
{
	_DBG();
	size_t len;
	unsigned minor_ = MINOR(filp->f_dentry->d_inode->i_rdev);
	int minor = (int) minor_;
	if ( buffers[minor] == NULL ) {
		buffers[minor] = kmalloc( ( sizeof(char) ) *BUFFER_SIZE, GFP_KERNEL);
	}

	if ( count == 0 || read_index[minor] > write_index[minor] ) { 
		return 0;
	}

	if ( read_index[minor] + count < write_index[minor] ){
		len = count;
	}else{
		len = write_index[minor] - read_index[minor];
	}
	unsigned long res = copy_to_user(buf,buffers[minor]+read_index[minor],len);
	if (res != 0) {
		return -ENOMEM;
	}
	read_index[minor] += len;
	return len; 
}


ssize_t my_write(struct file *filp, const char *buf, size_t count, loff_t *f_pos)
{
	_DBG();
	unsigned minor_ = MINOR(filp->f_dentry->d_inode->i_rdev);
	int minor = (int) minor_;
	if ( buffers[minor] == NULL ) {
		buffers[minor] = kmalloc( ( sizeof(char) ) *BUFFER_SIZE, GFP_KERNEL);
	}
	if ( ( !buffers[minor] ) || count < 0 ) {
		return -EINVAL;
	}
	if (count + write_index[minor] > BUFFER_SIZE){
		return -ENOMEM;
	}
	unsigned long res = copy_from_user(buffers[minor] + write_index[minor] , buf , count);
	if (res != 0) {
		return -ENOMEM;
	}
	write_index[minor] += count;
	return count; 
}


int my_ioctl(struct inode *inode, struct file *filp, unsigned int cmd, unsigned long arg)
{
	_DBG();
	unsigned minor_ = MINOR(inode->i_rdev);
	int minor = (int) minor_;
	switch(cmd)
	{
		case MY_RESET:
			read_index[minor] = 0;
			write_index[minor] = 0;
			break;

		case MY_RESTART:
			read_index[minor] = 0;
			break;

		default:
			return -ENOTTY;
	}
	return 0;
}
